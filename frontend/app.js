document.addEventListener('DOMContentLoaded', () => {
  const textInput = document.getElementById('text-input');
  const styleSelect = document.getElementById('style-select');
  const speedSelect = document.getElementById('speed-select');
  const fpsSelect = document.getElementById('fps-select');
  const btnPreview = document.getElementById('btn-preview');
  const btnRender = document.getElementById('btn-render');
  const statusMessage = document.getElementById('status-message');

  const placeholder = document.getElementById('preview-placeholder');
  const previewImageContainer = document.getElementById('preview-image-container');
  const previewImg = document.getElementById('preview-img');
  const videoContainer = document.getElementById('video-container');
  const resultVideo = document.getElementById('result-video');
  const jobsList = document.getElementById('jobs-list');

  const charCountEl = document.getElementById('char-count');
  const charCounterEl = document.getElementById('char-counter');
  const charLimitWarning = document.getElementById('char-limit-warning');
  const MAX_CHARS = 256;

  function updateCharCount() {
    const text = textInput.value;
    const len = text.length;
    if (charCountEl) {
      charCountEl.textContent = len;
    }

    if (len > MAX_CHARS) {
      if (charCounterEl) charCounterEl.classList.add('exceeded');
      textInput.classList.add('exceeded');
      if (charLimitWarning) {
        charLimitWarning.classList.remove('hidden');
        charLimitWarning.textContent = `⚠️ 文本长度已达 ${len} 字符，超出 ${MAX_CHARS} 字符上限（超出 ${len - MAX_CHARS} 字），请删减后再生成`;
      }
      return false;
    } else {
      if (charCounterEl) charCounterEl.classList.remove('exceeded');
      textInput.classList.remove('exceeded');
      if (charLimitWarning) charLimitWarning.classList.add('hidden');
      return true;
    }
  }

  textInput.addEventListener('input', updateCharCount);
  textInput.addEventListener('paste', () => setTimeout(updateCharCount, 20));

  // Preset chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      textInput.value = chip.dataset.text;
      updateCharCount();
    });
  });

  function showStatus(text, type = 'info') {
    statusMessage.textContent = text;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
  }

  function hideStatus() {
    statusMessage.classList.add('hidden');
  }

  function showPreviewImage(url) {
    placeholder.classList.add('hidden');
    videoContainer.classList.add('hidden');
    previewImg.src = url;
    previewImageContainer.classList.remove('hidden');
  }

  function showVideo(url) {
    placeholder.classList.add('hidden');
    previewImageContainer.classList.add('hidden');
    resultVideo.src = url;
    videoContainer.classList.remove('hidden');
  }

  // Load styles
  async function loadStyles() {
    try {
      const res = await fetch('/api/styles');
      if (res.ok) {
        const data = await res.json();
        if (data.styles && data.styles.length > 0) {
          styleSelect.innerHTML = '';
          data.styles.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `${s.name} - ${s.description}`;
            styleSelect.appendChild(opt);
          });
        }
      }
    } catch (e) {
      console.warn('Failed to load dynamic styles:', e);
    }
  }

  // Preview action
  btnPreview.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
      showStatus('请输入要书写的汉字', 'error');
      return;
    }
    if (text.length > MAX_CHARS) {
      showStatus(`输入文本超出上限：当前为 ${text.length} 字符，最大支持 ${MAX_CHARS} 字符。请删减后再试。`, 'error');
      return;
    }

    btnPreview.disabled = true;
    showStatus('正在生成静图预览...', 'info');

    try {
      const res = await fetch('/api/previews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          style: styleSelect.value
        })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '预览失败');
      }
      showPreviewImage(data.preview_url);
      showStatus('静图预览已就绪', 'info');
    } catch (err) {
      showStatus(`预览失败: ${err.message}`, 'error');
    } finally {
      btnPreview.disabled = false;
    }
  });

  // Render action
  btnRender.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
      showStatus('请输入要书写的汉字', 'error');
      return;
    }
    if (text.length > MAX_CHARS) {
      showStatus(`输入文本超出上限：当前为 ${text.length} 字符，最大支持 ${MAX_CHARS} 字符。请删减后再试。`, 'error');
      return;
    }

    btnRender.disabled = true;
    showStatus('正在提交视频生成任务...', 'info');

    try {
      const res = await fetch('/api/renders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          style: styleSelect.value,
          speed: parseFloat(speedSelect.value),
          fps: parseInt(fpsSelect.value, 10)
        })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '提交失败');
      }
      showStatus(`视频生成任务已排队 (${data.job_id})，正在后台书写...`, 'info');
      pollJob(data.job_id);
      loadJobs();
    } catch (err) {
      showStatus(`提交失败: ${err.message}`, 'error');
    } finally {
      btnRender.disabled = false;
    }
  });

  // Poll job status
  async function pollJob(jobId) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) {
          clearInterval(interval);
          return;
        }
        const job = await res.json();
        loadJobs();

        if (job.status === 'succeeded') {
          clearInterval(interval);
          showStatus('书写视频已成功生成！', 'info');
          if (job.download_url) {
            showVideo(job.download_url);
          }
        } else if (job.status === 'failed') {
          clearInterval(interval);
          showStatus(`生成失败: ${job.error_message || '未知错误'}`, 'error');
        } else {
          showStatus(`视频正在渲染中 (${Math.round(job.progress * 100)}%)...`, 'info');
        }
      } catch (e) {
        console.error(e);
      }
    }, 1500);
  }

  // Render jobs list
  async function loadJobs() {
    try {
      const res = await fetch('/api/jobs');
      if (!res.ok) return;
      const data = await res.json();
      const jobs = data.jobs || [];

      if (jobs.length === 0) {
        jobsList.innerHTML = '<p class="empty-jobs">暂无生成任务</p>';
        return;
      }

      jobsList.innerHTML = '';
      jobs.forEach(job => {
        const card = document.createElement('div');
        card.className = 'job-card';

        const info = document.createElement('div');
        info.className = 'job-info';

        const title = document.createElement('div');
        title.className = 'job-text';
        title.textContent = `${job.text} [${job.style}]`;

        const meta = document.createElement('div');
        meta.className = 'job-meta';
        const typeLabel = job.job_type === 'render' ? '视频' : '静图';
        meta.textContent = `${typeLabel} · ${new Date(job.created_at).toLocaleTimeString()}`;

        info.appendChild(title);
        info.appendChild(meta);

        const actions = document.createElement('div');
        actions.className = 'job-actions';

        const badge = document.createElement('span');
        badge.className = `badge ${job.status}`;
        badge.textContent = job.status === 'succeeded' ? '完成' :
                            (job.status === 'rendering' ? '渲染中' :
                            (job.status === 'queued' ? '排队中' : '失败'));
        actions.appendChild(badge);

        if (job.status === 'succeeded' && job.job_type === 'render') {
          const dl = document.createElement('a');
          dl.className = 'btn-download';
          dl.href = `/api/jobs/${job.job_id}/download`;
          dl.textContent = '下载 MP4';
          dl.setAttribute('download', `calligraphy_${job.job_id}.mp4`);
          dl.style.marginLeft = '8px';
          dl.addEventListener('click', (e) => {
            showVideo(`/api/jobs/${job.job_id}/download`);
          });
          actions.appendChild(dl);
        }

        card.appendChild(info);
        card.appendChild(actions);
        jobsList.appendChild(card);
      });
    } catch (e) {
      console.warn('Failed to load jobs list:', e);
    }
  }

  // Initialize
  updateCharCount();
  loadStyles();
  loadJobs();
});
