export function positiveInteger(value, name, { minimum = 1, even = false } = {}) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < minimum || (even && parsed % 2 !== 0)) {
    const evenMessage = even ? ' even' : '';
    throw new TypeError(`${name} must be an${evenMessage} integer >= ${minimum}`);
  }
  return parsed;
}

export function positiveNumber(value, name, { maximum = Infinity } = {}) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > maximum) {
    const range = Number.isFinite(maximum) ? ` in (0, ${maximum}]` : ' greater than 0';
    throw new TypeError(`${name} must be${range}`);
  }
  return parsed;
}

export function finiteNumber(value, name, { minimum = -Infinity, maximum = Infinity } = {}) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < minimum || parsed > maximum) {
    throw new TypeError(`${name} must be a finite number between ${minimum} and ${maximum}`);
  }
  return parsed;
}
