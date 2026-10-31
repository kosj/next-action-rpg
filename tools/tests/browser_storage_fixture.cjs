/* Controlled IndexedDB events only. The reader source is supplied by Python AST. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { performance } = require('node:perf_hooks');
const { TextEncoder, TextDecoder } = require('node:util');

global.performance = performance;
global.TextDecoder = TextDecoder;
const source = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const read = vm.runInThisContext('(' + source + ')', { filename: 'actual_browser_storage_reader.js' });
const primary = '/userfs/godot/app_userdata/RUNEFALL · 무너진 성역/runefall_v1.json';
const save = { version: 1, journey_started: true, checkpoint: 0, settings: { quality: 0 } };

function install(options = {}) {
  const metrics = { enumerations: 0, opens: 0, closed: 0, key_batches: 0,
    value_reads: [], modes: [], upgrade_aborted: false };
  const data = new Map([[primary, { timestamp: new Date(0),
    contents: new TextEncoder().encode(options.invalid ? '{bad' : JSON.stringify(save)) }]]);
  const unreadable = message => new Proxy({}, { get() { throw new Error(message); } });
  for (let index = 0; index < 200; index++) {
    data.set('/userfs/cache/opaque-' + index, unreadable('An unrelated file payload was read'));
  }
  data.set(primary + '.bak', unreadable('The backup payload was read'));
  global.window = {};
  const db = {
    objectStoreNames: { contains: name => !options.noStore && name === 'FILE_DATA' },
    close() { metrics.closed++; },
    transaction(name, mode) {
      assert.equal(name, 'FILE_DATA');
      assert.equal(mode, 'readonly');
      metrics.modes.push(mode);
      const transaction = {
        error: null, pending: 0, aborted: false,
        abort() { this.aborted = true; setImmediate(() => this.onabort?.()); },
        objectStore(name) { assert.equal(name, 'FILE_DATA'); return store; },
      };
      function request(value) {
        const item = { result: undefined };
        transaction.pending++;
        setImmediate(() => {
          item.result = value;
          try { item.onsuccess?.(); } catch (error) { transaction.error = error; transaction.abort(); }
          transaction.pending--;
          setImmediate(() => {
            if (transaction.pending === 0 && !transaction.aborted) transaction.oncomplete?.();
          });
        });
        return item;
      }
      const store = {
        getAllKeys() { metrics.key_batches++; return request([...data.keys()]); },
        get(key) { metrics.value_reads.push(key); assert.equal(key, primary); return request(data.get(key)); },
        openCursor() { throw new Error('A full value cursor is forbidden'); },
      };
      return transaction;
    },
  };
  global.indexedDB = {
    async databases() {
      metrics.enumerations++;
      return [{ name: '/userfs', version: 21 }, { name: 'unrelated', version: 1 }];
    },
    open(name) {
      assert.equal(name, '/userfs');
      metrics.opens++;
      const item = { result: db, error: null, transaction: { abort() {
        metrics.upgrade_aborted = true;
        item.error = Object.assign(new Error('Unexpected upgrade aborted'), { name: 'AbortError' });
        setImmediate(() => item.onerror?.());
      } } };
      setImmediate(() => { if (options.upgrade) item.onupgradeneeded?.(); else item.onsuccess?.(); });
      return item;
    },
  };
  return metrics;
}

const cases = {
  async discover_primary() {
    const metrics = install();
    const result = await read({ id: 1, targets: [] });
    assert.equal(result.saves.length, 1);
    assert.deepEqual(result.saves[0].save, save);
    assert.equal(metrics.key_batches, 1);
    assert.deepEqual(metrics.value_reads, [primary]);
    assert.deepEqual(metrics.modes, ['readonly']);
    assert.equal(result.diagnostic.key_count, 202);
    assert.equal(result.diagnostic.primary_reads, 1);
    return metrics;
  },
  async cached_lookup() {
    install();
    const discovered = await read({ id: 1, targets: [] });
    const metrics = install();
    const result = await read({ id: 2, targets: discovered.targets });
    assert.equal(metrics.enumerations, 0);
    assert.equal(metrics.key_batches, 0);
    assert.deepEqual(metrics.value_reads, [primary]);
    assert.deepEqual(metrics.modes, ['readonly']);
    assert.equal(result.saves[0].save.settings.quality, 0);
    return metrics;
  },
  async missing_store() {
    const metrics = install({ noStore: true });
    const result = await read({ id: 3, targets: [] });
    assert.equal(result.saves.length, 0);
    assert.equal(metrics.closed, 1);
    assert.deepEqual(metrics.value_reads, []);
    assert.deepEqual(metrics.modes, []);
    return metrics;
  },
  async abort_upgrade() {
    const metrics = install({ upgrade: true });
    await assert.rejects(read({ id: 4, targets: [] }), error => error.name === 'AbortError');
    assert.equal(metrics.upgrade_aborted, true);
    assert.deepEqual(metrics.modes, []);
    return metrics;
  },
  async malformed_primary() {
    const metrics = install({ invalid: true });
    await assert.rejects(read({ id: 5, targets: [] }), SyntaxError);
    assert.equal(metrics.closed, 1);
    assert.deepEqual(metrics.modes, ['readonly']);
    return metrics;
  },
};

(async () => {
  const selected = process.argv[3] || 'all';
  const names = selected === 'all' ? Object.keys(cases) : [selected];
  const results = [];
  for (const name of names) {
    assert.ok(Object.hasOwn(cases, name), 'Unknown fixture case: ' + name);
    results.push({ id: name, status: 'passed', metrics: await cases[name]() });
  }
  console.log(JSON.stringify({ schema_version: 1, status: 'passed', node_version: process.version,
    scope: 'Controlled Node IndexedDB events: readonly requests, key discovery, primary-only reads, upgrade abort and invalid-data rejection. This is not real-browser persistence or a performance benchmark.',
    cases: results }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
