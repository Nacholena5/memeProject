# Arquitectura recomendada para scanner local-first de Solana meme coins

## 1. Qué hacen en común estas herramientas similares

Las plataformas públicas como GMGN, Photon, BullX, Nansen, Arkham, Bubblemaps, Birdeye y DexScreener comparten una arquitectura en capas:
- ingestión / discovery de nuevos tokens y pares
- validación de datos de mercado y pares principales
- scoring multi-dimensional
- reglas de seguridad / gating de identidad
- watchlist / discard funnel
- dashboards con estado operativo y explicación
- tiempo real / near real-time sobre datos on-chain y DEX

Probablemente se apoyan en:
- un motor de ingestión destinado a múltiples fuentes (DEX, indexers, alertas, listados recientes)
- snapshots históricos de precio, volumen, liquidez, transacciones
- una capa de validación de pares principales (pair quality / pool quality)
- scoring combinado con pesos conservadores y reglas de gate
- recolección de flags de riesgo en cada etapa
- almacenamiento de sesiones de escaneo, entries de watchlist, discard y explicaciones
- APIs REST para consumir catálogos, señales, historial y detalle por token
- un dashboard operable que prioriza la lista procesable frente a lo descartado

## 2. Señales que valen la pena copiar/adaptar

Se pueden adaptar con prudencia estas señales públicas:
- edad del token + recency del listing
- liquidez USD y volumen 1h/4h
- transacciones y ratio buys/sells
- price change 5m/1h, volumen acelerado
- validación de pair principal en DEX recientes
- boosts / paid orders como indicadores de publicidad pagada
- organic flow / promo flow divergence
- whale accumulation y smart-money presence
- repeated buyers / net whale inflows
- demand quality: tx count, buyer distribution, continuidad
- ownership concentration / holder clusters
- breakout timing: overextension, consolidation, entry timing
- identidad/provenance confirmada vs inferred vs fallback
- gating de metadata conflict

Estas señales son útiles siempre que sean secundarias a:
- liquidez real
- calidad de datos
- identidad
- riesgo detectado

## 3. Qué partes NO copiaría o trataría con mucha cautela

- public ranking de hype sin validación on-chain
- claims absolutos de “insider money” sin demo de wallet labeling real
- señales basadas solo en influencers/KOLs o tendencias sociales
- pipelines que tratan paid boost como “insta-long”
- sistemas que elevan tokens muy extendidos (+300%/+500%) solo por momentum
- cruces de datos incompletos que no penalizan identidad fallback
- análisis de holder graphs sin contexto de volumen y liquidity
- “paper short” como recomendación para traders reales (para ahora solo desde research)

## 4. Arquitectura recomendada para tu sistema

### Módulos principales

1. `discovery`
   - ingestión de Birdeye, DexScreener y fallback de search
   - candidates early-stage con edad, liquidity, volume, txs, buys/sells

2. `market data`
   - validación de pares principales
   - snapshots de liquidez, volumen, spreads, paid boosts
   - market context BTC / SOL trend

3. `wallet intelligence`
   - wallet flow snapshots
   - whale accumulation, smart wallet presence
   - repeated buyers, insider risk, dev sell pressure

4. `holder/cluster analysis`
   - holder concentration snapshots
   - suspicious cluster score
   - connected wallet clusters

5. `risk/security`
   - flags de promo flow divergence
   - liquidity fragile
   - suspicious vertical pump
   - insufficient pair quality
   - identity gates

6. `provenance`
   - token metadata pipeline
   - confirm/infer/fallback/unverified
   - metadata_conflict
   - identity quality score

7. `social/narrative`
   - narrative strength
   - meme clarity
   - paid vs organic gap
   - bot suspicion

8. `timing`
   - breakout setup score
   - entry timing score
   - invalidation quality
   - overextension penalty

9. `scoring`
   - dimension snapshots
   - composite score + gate notes

10. `watchlist/funnel`
    - watchlist entries
    - discarded entries
    - funnel metrics
    - operability status

11. `explainability`
    - razones y explicación por token
    - qué capas penalizan y qué capas favorecen
    - qué tendría que cambiar

12. `exit planning`
    - target ladder y stop/invalidation zones
    - plan parcial de take-profit
    - no trade si no hay salida clara

## 5. Features y sub-scores concretos

### Discovery layer
- token_age_minutes
- liquidity_usd
- volume_1h_usd
- transactions_1h
- buys_sells_ratio
- price_change_5m / price_change_1h
- volume_acceleration
- boosts_active
- paid_orders
- activity_score
- new_pair flag

### Wallet / whale layer
- whale_accumulation_score
- smart_wallet_presence_score
- net_whale_inflow
- repeated_buyer_score
- insider_risk_score
- dev_sell_pressure_score
- wallet_flow_score
- labeled_wallet_count

### Demand quality layer
- transaction_demand_score
- tx_count_acceleration
- organic_volume_score
- wash_trading_suspicion_score
- buyer_distribution_score
- trade_continuity_score

### Identity / provenance layer
- metadata_source
- metadata_confidence
- metadata_is_fallback
- metadata_last_source
- metadata_last_validated_at
- metadata_conflict
- identity_quality_score
- identity_gate_reason
- identity_rule_applied
- identity_confidence_cap

### Paid attention / shill layer
- paid_attention_high flag
- promo_flow_divergence flag
- boost_intensity (boosts_active)
- paid_vs_organic_narrative_gap
- paid_vs_organic_gap
- ad_presence

### Narrative / social layer
- social_velocity_score
- community_growth_score
- organic_engagement_score
- bot_suspicion_score
- narrative_strength_score
- meme_clarity_score
- cross_source_narrative_score
- narrative_repetition_score
- social_wallet_divergence_score
- cult_signal_score

### Breakout / timing layer
- breakout_setup_score
- consolidation_quality_score
- breakout_confirmation_score
- overextension_penalty
- entry_timing_score
- invalidation_quality_score

### Exit planning
- target ladder proposed
- partial take profit plan
- invalidation zone
- stop-loss suggestion
- degen risk label
- plan viability check

## 6. Clasificación final y reglas

### Categorías finales
- LONG ahora
- WATCHLIST prioritaria
- WATCHLIST secundaria
- SHORT solo paper
- IGNORE
- NO TRADE

### Reglas de decisión
- no LONG si identity es fallback / unverified
- metadata_conflict penaliza fuerte y debe forzar NO TRADE o watchlist
- paid attention alto + flujo orgánico débil => NO TRADE o WATCHLIST secundaria
- liquidez frágil / pair débil => NO TRADE / IGNORE
- si el token ya está sobreextendido, bajar a WATCHLIST secundaria
- si no hay recomendación de salida razonable, penalizar confianza
- si detecta wash trading o bot divergence, NO TRADE
- score solo no basta: combinar identity, riesgo, data quality, liquidity, demand, timing, paid vs organic, market context

### Operabilidad
- `LONG ahora` = operable hoy
- `WATCHLIST prioritaria` = monitor urgente
- `WATCHLIST secundaria` = monitor amplio
- `SHORT solo paper` = research, no trade automático
- `IGNORE` = no edge actual
- `NO TRADE` = bloqueado por seguridad o datos

## 7. Tablas / endpoints

### Tablas principales (ya presentes en el código)
- `tokens`
- `score_snapshots`
- `scan_sessions`
- `discovery_candidates`
- `dexscreener_validations`
- `watchlist_entries`
- `discarded_entries`
- `whale_signal_snapshots`
- `social_signal_snapshots`
- `demand_signal_snapshots`
- `narrative_signal_snapshots`
- `breakout_signal_snapshots`
- `signal_composite_snapshots`
- `wallet_flow_snapshots`
- `holder_distribution_snapshots`
- `scanner_flags`
- `alerts_sent`
- `signal_outcomes`
- `performance_reports`

### Tablas recomendadas para completar
- `paid_attention_snapshots`
- `exit_plan_snapshots`
- `token_explanations` (opcional)
- `market_context_snapshots` (opcional)

### Endpoints clave existentes
- `/market/context`
- `/quality/summary`
- `/signals/latest`
- `/signals/top`
- `/scanner/run`
- `/scanner/watchlist/today`
- `/scanner/discarded/today`
- `/scanner/funnel/latest`
- `/scanner/token/{address}`
- `/scanner/token/{address}/signals`
- `/wallets/top`
- `/wallets/token/{address}`
- `/breakouts/latest`
- `/narratives/latest`
- `/tokens/{address}/explain`
- `/tokens/{address}/history`

### Endpoints recomendados a agregar
- `/scanner/paid-attention/latest`
- `/exit-plans/latest`
- `/scanner/sessions/latest`
- `/scanner/flags/latest`
- `/tokens/{address}/exit-plan`
- `/scanner/reports/performance`

## 8. Dashboard recomendado

Priorizar las secciones en este orden:
1. operables hoy (`LONG ahora`)
2. watchlist diaria (`WATCHLIST prioritaria`, `WATCHLIST secundaria`)
3. bloqueadas / no trade
4. funnel de discovery → validation → classification
5. señales modelo / dimension snapshots

Widgets clave:
- top whale accumulation
- top demand quality
- top breakout setup
- top paid-attention risk
- top narrative strength
- watchlist drawer enriquecido
- filtros por:
  - identidad
  - riesgo
  - liquidez
  - calidad de datos
  - tiempo de token
  - paid attention

El dashboard debe mostrar para cada token:
- categoría + operabilidad
- razón principal + explicación corta
- identidad / provenance
- liquidez / volumen / pair quality
- score long / short / confidence
- flags de riesgo
- plan de salida sugerido

## 9. Roadmap incremental

### Fase 1 (base ya soportada en el código actual)
- discovery (`birdeye`, DexScreener fallback)
- market data / validación de pairs
- provenance / metadata
- watchlist / discarded funnel
- endpoints básicos de scanner

### Fase 2
- wallet/whale intelligence
- demand quality snapshots
- explainability detallada por token
- refinar gating de identidad

### Fase 3
- breakout timing
- paid attention / promo_flow divergence
- exit planning snapshots y plan sugerido

### Fase 4
- social / narrative layer
- holder/cluster visualization
- cluster previews en holder_distribution
- dashboard de mapas de concentración

### Fase 5
- hardening
- tests unitarios e integración
- documentación + scripts de despliegue / run
- optimización de ingestión y fallback

## 10. Próximos pasos concretos

1. reforzar `exit_plan_snapshots` con reglas de invalidation y target ladder
2. agregar endpoint `/scanner/paid-attention/latest` y exponer flags de `dexscreener_validations`
3. formalizar `token_explanations` o usar `payload_json` de watchlist para explicabilidad
4. mejorar dashboard para distinguir “operable hoy” vs “watchlist” vs “no trade”
5. añadir tests sobre gated decisions y flags de paid attention
6. documentar la lógica de scoring y gating en `docs/`

---

### Nota de implementación actual

El código actual ya cuenta con:
- scoring multi-dimensional en `app/services/signal_dimension_service.py`
- gating de identidad en `app/services/identity_classification_service.py`
- watchlist / funnel / payloads en `app/services/playbook_scanner_service.py`
- endpoints REST en `app/api/routes_scanner.py`, `routes_wallets.py`, `routes_quality.py`, `routes_market.py`, `routes_tokens.py`, `routes_narratives.py`, `routes_breakouts.py`

Eso significa que ya tienes una base sólida y que el siguiente paso natural es completar las piezas faltantes de paid attention y exit planning, más la visualización operativa.
