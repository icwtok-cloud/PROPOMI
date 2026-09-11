'use client';
import { useMemo, useState } from 'react';
import { Property, Intent } from '../lib/types';
import { createOffer, saveIntent, trackEvent } from '../lib/api';

type PaymentForm = 'CASH' | 'FINANCING' | 'MIXED';
type Timeframe = '15 días' | '30-60 días' | '60-90 días' | 'A convenir';
type CapitalRange = '<50k' | '50-100k' | '100-150k' | '150k+';
type ConditionKey = 'inspeccion' | 'escribania' | 'mudanza' | 'inmediata' | 'permuta';

const CAPITAL_LABELS: Record<CapitalRange, string> = {
  '<50k': 'Menos de USD 50k',
  '50-100k': 'USD 50k – 100k',
  '100-150k': 'USD 100k – 150k',
  '150k+': 'Más de USD 150k',
};

const PAYMENT_LABELS: Record<PaymentForm, string> = {
  CASH: 'Contado',
  FINANCING: 'Financiado',
  MIXED: 'Mixta',
};

const CONDITION_LABELS: Record<ConditionKey, string> = {
  inspeccion: 'Sujeto a inspección',
  escribania: 'Escribanía propia',
  mudanza: 'Mudanza flexible',
  inmediata: 'Entrega inmediata',
  permuta: 'Tengo otra propiedad para entregar o vender',
};

const TOTAL_STEPS = 4;

export default function OfferModal({ p, onClose, onDone }: { p: Property; onClose: () => void; onDone: (msg: string) => void }) {
  const [step, setStep] = useState(1);
  const [amount, setAmount] = useState(Math.round(p.price * 0.95));
  const [capital, setCapital] = useState<CapitalRange>('50-100k');
  const [form, setForm] = useState<PaymentForm>('MIXED');
  const [timeframe, setTimeframe] = useState<Timeframe>('30-60 días');
  const [conditions, setConditions] = useState<ConditionKey[]>([]);
  const [busy, setBusy] = useState(false);

  const minAmount = Math.round(p.price * 0.7);
  const quickPcts = [0.85, 0.9, 0.95, 1.0];

  function toggleCondition(key: ConditionKey) {
    setConditions((prev) => (prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]));
  }

  const conditionsText = useMemo(
    () => (conditions.length ? conditions.map((c) => CONDITION_LABELS[c]).join(', ') : 'Sin condiciones adicionales'),
    [conditions]
  );

  async function send() {
    setBusy(true);
    const comment = conditions.map((c) => CONDITION_LABELS[c]).join('; ');
    const capitalMidpoint = { '<50k': 40000, '50-100k': 75000, '100-150k': 125000, '150k+': 175000 }[capital];
    const data: Intent = {
      offer: true,
      budget: p.price,
      capital: capitalMidpoint,
      financing: form === 'FINANCING' ? 'YES' : 'NO',
      timeframe,
      alternatives: conditions.includes('permuta'),
      comment,
    };
    await createOffer({ property_id: p.id, amount, payment_form: form, capital: capitalMidpoint, timeframe, comment });
    await saveIntent(p.id, 'OFFER', 8, data);
    await trackEvent('offer_created', p.id, { amount });
    setBusy(false);
    onDone('Oferta enviada. Resguardamos tus datos por seguridad y para que no recibas spam innecesario. Del otro lado tienen 24 hs para responderte: si no contestan, es simplemente porque no tienen nada que ofrecerte.');
  }

  function next() {
    if (step < TOTAL_STEPS) setStep(step + 1);
    else send();
  }
  function back() {
    if (step > 1) setStep(step - 1);
  }

  return (
    <div className="modalback">
      <div className="modal offerwizard">
        <div className="modalhead">
          <div>
            <span className="eyebrow">Negociación</span>
            <h2>Proponer un precio</h2>
            <p className="muted">
              {p.title} · USD {p.price.toLocaleString('en-US')} · Paso {step} de {TOTAL_STEPS}
            </p>
          </div>
          <button className="close" onClick={onClose}>×</button>
        </div>

        <div className="wizprogress">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <span key={i} className={i < step ? 'done' : ''} />
          ))}
        </div>

        {step === 1 && (
          <div className="wizstep">
            <div className="qlabel">¿Cuánto querés ofrecer?</div>
            <div className="qhelp">Movés el control o elegís un atajo rápido.</div>
            <div className="sliderbox">
              <div className="slidervalue">USD {amount.toLocaleString('en-US')}</div>
              <div className="sliderref">Precio publicado: USD {p.price.toLocaleString('en-US')}</div>
              <input
                type="range"
                min={minAmount}
                max={p.price}
                step={1000}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
              <div className="quickrow">
                {quickPcts.map((pct) => {
                  const val = Math.round((p.price * pct) / 1000) * 1000;
                  const label = pct === 1 ? 'Precio publicado' : `${Math.round((1 - pct) * 100)}%`;
                  return (
                    <button
                      key={pct}
                      type="button"
                      className={amount === val ? 'quickbtn active' : 'quickbtn'}
                      onClick={() => setAmount(val)}
                    >
                      {pct === 1 ? label : `−${label}`}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="wizstep">
            <div className="qlabel">¿Con qué capital contás hoy?</div>
            <div className="qhelp">Un rango alcanza, no hace falta el monto exacto.</div>
            <div className="chipgrid">
              {(Object.keys(CAPITAL_LABELS) as CapitalRange[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  className={capital === key ? 'wchip selected' : 'wchip'}
                  onClick={() => setCapital(key)}
                >
                  {CAPITAL_LABELS[key]}
                </button>
              ))}
            </div>

            <div className="qlabel">¿Cómo pensás pagar?</div>
            <div className="chipgrid triple">
              {(Object.keys(PAYMENT_LABELS) as PaymentForm[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  className={form === key ? 'wchip selected' : 'wchip'}
                  onClick={() => setForm(key)}
                >
                  {PAYMENT_LABELS[key]}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="wizstep">
            <div className="qlabel">¿En cuánto tiempo querés cerrar?</div>
            <div className="chipgrid">
              {(['15 días', '30-60 días', '60-90 días', 'A convenir'] as Timeframe[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  className={timeframe === key ? 'wchip selected' : 'wchip'}
                  onClick={() => setTimeframe(key)}
                >
                  {key}
                </button>
              ))}
            </div>

            <div className="qlabel">¿Alguna condición para agregar?</div>
            <div className="qhelp small">Elegí todas las que apliquen (opcional)</div>
            <div className="chipgrid">
              {(Object.keys(CONDITION_LABELS) as ConditionKey[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  className={conditions.includes(key) ? (key === 'permuta' ? 'wchip selected wide' : 'wchip selected') : key === 'permuta' ? 'wchip wide' : 'wchip'}
                  onClick={() => toggleCondition(key)}
                >
                  {CONDITION_LABELS[key]}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="wizstep">
            <div className="qlabel">Revisá tu propuesta</div>
            <div className="qhelp">Podés volver atrás y cambiar cualquier punto.</div>
            <div className="summarycard">
              <div className="summaryrow"><span>Monto de oferta</span><b>USD {amount.toLocaleString('en-US')}</b></div>
              <div className="summaryrow"><span>Capital disponible</span><b>{CAPITAL_LABELS[capital]}</b></div>
              <div className="summaryrow"><span>Forma de pago</span><b>{PAYMENT_LABELS[form]}</b></div>
              <div className="summaryrow"><span>Plazo</span><b>{timeframe}</b></div>
              <div className="summaryrow"><span>Condiciones</span><b>{conditionsText}</b></div>
            </div>
            <div className="notice">
              Resguardamos tus datos por seguridad y para que no recibas spam innecesario. Del otro lado tienen{' '}
              <b>24 hs para responderte</b>: si no contestan, es simplemente porque no tienen nada que ofrecerte.
            </div>
          </div>
        )}

        <div className="modalactions wizactions">
          <button className="secondary" onClick={step === 1 ? onClose : back}>
            {step === 1 ? 'Cancelar' : 'Atrás'}
          </button>
          <button className="primary" disabled={busy} onClick={next}>
            {busy ? 'Enviando…' : step === TOTAL_STEPS ? 'Enviar oferta' : 'Continuar'}
          </button>
        </div>
      </div>
    </div>
  );
}
