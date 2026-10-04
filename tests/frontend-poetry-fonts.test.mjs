import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const catalog = JSON.parse(await readFile(new URL('../data/calligraphy_fonts.json', import.meta.url)));
const fonts = [
  ['lxgw-wenkai-tc', 'lxgw-wenkai-tc', 'LXGWWenKaiTC'],
  ['iansui-kai', 'iansui-kai', 'Iansui'],
  ['lxgw-zhenkai', 'lxgw-zhenkai', 'LXGWZhenKai'],
  ['hanwang-lisu-medium', 'lishu hanwang', 'HanWangLiSuMedium'],
  ['qiji-font-kai', 'qiji-kai', 'Qiji'],
];
for (const [id, style, family] of fonts) {
  test(`${id} is discoverable, selects its real face and exports the canonical style`, async t => {
    const ui = await createFrontend({ fetch({ url }) {
      if (url === '/api/font-catalog') return jsonResponse(catalog);
      if (url === '/api/styles') return jsonResponse({ styles: fonts.map(([id, style]) => ({ id: style, name: id, description: '' })) });
      if (url === '/api/convert-script') return jsonResponse({ text: '明月松間照', target: 'trad' });
      if (url === '/api/previews') return jsonResponse({ preview_url: '/test.png' });
    }});
    t.after(ui.close);
    const button = ui.document.querySelector(`.btn-try[data-id="${id}"]`);
    assert.ok(button, 'visible under the default traditional filter');
    button.click();
    await flush();
    assert.equal(ui.document.getElementById('style-select').value, style);
    assert.match(ui.document.getElementById('calligraphy-text').style.fontFamily, new RegExp(family));
    assert.match(ui.document.getElementById('active-font-badge').textContent, new RegExp(catalog.find(f => f.id === id).name_zh));
    ui.document.getElementById('btn-preview').click();
    await flush();
    assert.equal(ui.requests.find(r => r.url === '/api/previews').body.style, style);
  });
}
