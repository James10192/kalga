/**
 * Tests du MessageBuffer — runner natif node:test, horloge factice.
 * Lancer : node --test tests/
 */
const { test } = require('node:test');
const assert = require('node:assert');
const { MessageBuffer } = require('../src/utils/messageBuffer');

/** Horloge contrôlable : les timers ne tirent que sur fire(). */
function fakeClock() {
    const callbacks = new Map();
    let nextId = 0;
    return {
        set: (fn, _ms) => { const id = ++nextId; callbacks.set(id, fn); return id; },
        clear: (id) => callbacks.delete(id),
        async fire() {
            const fns = [...callbacks.values()];
            callbacks.clear();
            for (const fn of fns) await fn();
        },
        armed: () => callbacks.size,
    };
}

function makeBuffer(onFlush, clock, opts = {}) {
    return new MessageBuffer({
        onFlush,
        setTimeoutFn: clock.set,
        clearTimeoutFn: clock.clear,
        ...opts,
    });
}

test('une rafale est fusionnée en UN seul lot', async () => {
    const clock = fakeClock();
    const batches = [];
    const buf = makeBuffer(async (key, items) => batches.push(items), clock);

    buf.push('m|c', { text: 'je peux avoir le prix' });
    buf.push('m|c', { text: 'et des photos' });
    await clock.fire();

    assert.strictEqual(batches.length, 1);
    assert.deepStrictEqual(batches[0].map(i => i.text),
        ['je peux avoir le prix', 'et des photos']);
});

test('chaque nouveau message prolonge la fenêtre (un seul timer armé)', () => {
    const clock = fakeClock();
    const buf = makeBuffer(async () => {}, clock);

    buf.push('m|c', { text: 'a' });
    buf.push('m|c', { text: 'b' });
    buf.push('m|c', { text: 'c' });

    assert.strictEqual(clock.armed(), 1);
});

test('sérialisation : un message arrivé PENDANT le traitement forme le lot suivant', async () => {
    const clock = fakeClock();
    const batches = [];
    let release;
    const gate = new Promise(resolve => { release = resolve; });

    const buf = makeBuffer(async (key, items) => {
        batches.push(items.map(i => i.text));
        if (batches.length === 1) {
            // Pendant que le lot 1 est en cours, un nouveau message arrive
            buf.push('m|c', { text: 'tardif' });
            await gate;
        }
    }, clock);

    buf.push('m|c', { text: 'premier' });
    const flushing = clock.fire();
    release();
    await flushing;

    assert.deepStrictEqual(batches, [['premier'], ['tardif']]);
});

test('flushNow vide immédiatement sans attendre la fenêtre', async () => {
    const clock = fakeClock();
    const batches = [];
    const buf = makeBuffer(async (key, items) => batches.push(items), clock);

    buf.push('m|c', { text: 'vocal arrive juste après' });
    await buf.flushNow('m|c');

    assert.strictEqual(batches.length, 1);
    assert.strictEqual(clock.armed(), 0);
});

test('les clients sont indépendants (clés séparées)', async () => {
    const clock = fakeClock();
    const byKey = {};
    const buf = makeBuffer(async (key, items) => { byKey[key] = items.length; }, clock);

    buf.push('m|client1', { text: 'a' });
    buf.push('m|client1', { text: 'b' });
    buf.push('m|client2', { text: 'x' });
    await clock.fire();

    assert.strictEqual(byKey['m|client1'], 2);
    assert.strictEqual(byKey['m|client2'], 1);
});

test('une erreur de traitement ne casse pas la boucle (onError appelé)', async () => {
    const clock = fakeClock();
    const errors = [];
    const buf = makeBuffer(
        async () => { throw new Error('API morte'); },
        clock,
        { onError: (e, key) => errors.push(`${key}:${e.message}`) }
    );

    buf.push('m|c', { text: 'boom' });
    await clock.fire();

    assert.deepStrictEqual(errors, ['m|c:API morte']);
    // Le buffer reste utilisable après l'erreur
    buf.push('m|c', { text: 'suite' });
    assert.strictEqual(clock.armed(), 1);
});
