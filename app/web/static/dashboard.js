let outcomesChart;
let metricsChart;
let tokenHistoryChart;

const STATE = {
  latest: [],
  topLong: [],
  topShort: [],
  signalQuery: "",
  scannerIdentity: "",
  operabilityFilter: "",
  riskFilter: "",
  hideFallback: false,
  lastValidTs: null,
  globalStatus: "Cargando...",
};

const PLACEHOLDER = {
  ND: "N/D",
  NO_DATA: "Sin datos",
  CONNECTION_ERROR: "Error de conexión",
  LOADING: "Cargando...",
};

const fmtPct = (v) => `${(Number(v) * 100).toFixed(1)} %`;
const fmtNum = (v, d = 2) => Number(v).toFixed(d);
const fmtTime = (iso) => {
  if (!iso) return "N/D";
  return new Date(iso).toLocaleString("es-UY", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} en ${url}`);
  return res.json();
}

async function getJsonSafe(url) {
  try {
    return await getJson(url);
  } catch (_e) {
    return null;
  }
}

function shortAddr(addr) {
  if (!addr) return PLACEHOLDER.ND;
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

function normalizeChain(chain) {
  const raw = String(chain || "").trim().toLowerCase();
  if (!raw) return "solana";
  if (raw === "sol") return "solana";
  return raw;
}

function identityFromRow(row) {
  const address = String(row?.token_address || "");
  const symbolRaw = String(row?.symbol || row?.token_symbol || "").trim();
  const nameRaw = String(row?.name || row?.token_name || "").trim();
  const symbol = symbolRaw && !["TOKEN", "UNK", "UNKNOWN", "N/A"].includes(symbolRaw.toUpperCase())
    ? symbolRaw.toUpperCase()
    : (nameRaw && !["token sin nombre", "unknown token", "token"].includes(nameRaw.toLowerCase()) ? nameRaw.slice(0, 10).toUpperCase() : `TK-${address.slice(0, 4).toUpperCase()}`);
  const name = nameRaw && !["token sin nombre", "unknown token", "token"].includes(nameRaw.toLowerCase())
    ? nameRaw
    : `Token ${shortAddr(address)}`;
  const chain = normalizeChain(row?.chain);
  const principalPair = String(row?.principal_pair || "").trim();
  const metadataSource = String(row?.metadata_source || "unknown").trim().toLowerCase();
  const metadataConfidence = String(row?.metadata_confidence || "unverified").trim().toLowerCase();
  const metadataIsFallback = Boolean(row?.metadata_is_fallback) || ["fallback", "unverified"].includes(metadataConfidence);
  const metadataLastSource = String(row?.metadata_last_source || metadataSource || "unknown").trim().toLowerCase();
  const metadataLastValidatedAt = String(row?.metadata_last_validated_at || "").trim();
  const metadataConflict = Boolean(row?.metadata_conflict);
  const isUncertain = metadataConflict || metadataIsFallback || metadataConfidence !== "confirmed";
  return {
    symbol,
    name,
    shortAddress: shortAddr(address),
    address,
    chain,
    principalPair,
    metadataSource,
    metadataConfidence,
    metadataIsFallback,
    metadataLastSource,
    metadataLastValidatedAt,
    metadataConflict,
    isUncertain,
  };
}

function metadataConfidenceLabel(value) {
  const map = {
    confirmed: "Confirmado",
    inferred: "Inferido",
    fallback: "Fallback",
    unverified: "Sin verificar",
  };
  return map[String(value || "").toLowerCase()] || "Sin verificar";
}

function metadataSourceLabel(value) {
  const map = {
    birdeye: "Birdeye",
    dexscreener: "DexScreener",
    onchain: "Onchain",
    local_fallback: "Local fallback",
    unknown: "Unknown",
  };
  return map[String(value || "").toLowerCase()] || String(value || "Unknown");
}

function metaConfidenceClass(value) {
  return `meta-confidence-${String(value || "unverified").toLowerCase()}`;
}

function metaSourceClass(value) {
  return `meta-source-${String(value || "unknown").toLowerCase()}`;
}

function renderMetaBadges(identity) {
  const confidence = identity.metadataConfidence || "unverified";
  const source = identity.metadataSource || "unknown";
  const fallbackClass = identity.metadataIsFallback ? "meta-warning" : "meta-ok";
  const conflictBadge = identity.metadataConflict ? '<span class="meta-badge meta-warning">Conflicto</span>' : "";
  return `
    <span class="meta-badge ${metaConfidenceClass(confidence)}">${metadataConfidenceLabel(confidence)}</span>
    <span class="meta-badge ${metaSourceClass(source)}">${metadataSourceLabel(source)}</span>
    <span class="meta-badge ${fallbackClass}">${identity.metadataIsFallback ? "Fallback" : "Real"}</span>
    ${conflictBadge}
  `;
}

function normalizeSearch(text) {
  return String(text || "").trim().toLowerCase();
}

function rowMatchesSignalQuery(row, normalizedQuery) {
  if (!normalizedQuery) {
    return true;
  }
  const identity = identityFromRow(row);
  const haystack = [identity.symbol, identity.name, identity.address, identity.principalPair].join(" ").toLowerCase();
  return haystack.includes(normalizedQuery);
}

function operabilityLabel(status) {
  const map = {
    operable: "Operable",
    watchlist: "Watchlist",
    bloqueado: "Bloqueado",
    no_trade: "No trade",
  };
  return map[String(status || "").toLowerCase()] || "Watchlist";
}

function operabilityClass(status) {
  return `operability-badge operability-${String(status || "watchlist").toLowerCase()}`;
}

function normalizeRiskFilterValue(value) {
  if (!value) return "";
  if (value === "low") return "riesgo bajo";
  if (value === "medium") return "riesgo medio";
  if (value === "high") return "riesgo alto";
  return String(value || "").toLowerCase();
}

function rowMatchesUiFilters(row) {
  const identity = identityFromRow(row);
  const normalizedOperability = String(row?.operability_status || "").toLowerCase();
  const rowRisk = getRisk(row).label.toLowerCase();

  if (STATE.hideFallback && (identity.metadataIsFallback || ["fallback", "unverified"].includes(identity.metadataConfidence))) {
    return false;
  }

  if (STATE.operabilityFilter && normalizedOperability !== STATE.operabilityFilter) {
    return false;
  }

  const normalizedRiskFilter = normalizeRiskFilterValue(STATE.riskFilter);
  if (normalizedRiskFilter && rowRisk !== normalizedRiskFilter) {
    return false;
  }

  return true;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setHtml(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = value;
}

function setLoading(isLoading) {
  const btn = document.getElementById("refreshBtn");
  if (!btn) return;
  btn.disabled = isLoading;
  btn.textContent = isLoading ? "Actualizando..." : "Actualizar";

  const banner = document.getElementById("globalLoading");
  if (banner) {
    banner.classList.toggle("hidden", !isLoading);
  }
}

function toggleBackendDown(show) {
  const el = document.getElementById("backendDownState");
  if (el) {
    el.classList.toggle("hidden", !show);
  }

  const lastValid = document.getElementById("lastValidUpdate");
  if (!lastValid) return;

  if (!show || !STATE.lastValidTs) {
    lastValid.classList.add("hidden");
    return;
  }

  const mins = Math.max(1, Math.round((Date.now() - STATE.lastValidTs.getTime()) / 60000));
  lastValid.textContent = `Última actualización válida: hace ${mins} min`;
  lastValid.classList.remove("hidden");
}

function toggleEmptyState(id, show) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle("hidden", !show);
  }
}

function dedupeByToken(rows) {
  const safeRows = asArray(rows);
  const map = new Map();
  safeRows.forEach((row) => {
    if (!row || !row.token_address) {
      return;
    }
    if (!map.has(row.token_address)) {
      map.set(row.token_address, row);
    }
  });
  return Array.from(map.values());
}

function setGlobalStatus(status) {
  STATE.globalStatus = status;
  const badge = document.getElementById("execStatusBadge");
  if (!badge) return;

  badge.className = "badge";
  if (status === "Operativo") {
    badge.classList.add("badge-ok");
  } else if (status === "Degradado") {
    badge.classList.add("badge-warn");
  } else if (status === "Sin conexión") {
    badge.classList.add("badge-bad");
  } else {
    badge.classList.add("badge-info");
  }
  badge.textContent = status;
}

function clearUiForConnectionError() {
  setText("execBias", PLACEHOLDER.NO_DATA);
  setText("execRisk", PLACEHOLDER.ND);
  setText("execBestLong", PLACEHOLDER.NO_DATA);
  setText("execBestShort", PLACEHOLDER.NO_DATA);
  setText("execReason", "No hay conexión activa para actualizar la lectura del sistema.");

  setText("ctxBtc", PLACEHOLDER.ND);
  setText("ctxSol", PLACEHOLDER.ND);
  setText("ctxMeme", PLACEHOLDER.ND);
  setText("ctxLiq", PLACEHOLDER.ND);
  setText("ctxFreshness", "Fuente: sin conexión");
  setText("ctxConfidence", "Confianza: N/D");

  const qualityBadge = document.getElementById("qualityBadge");
  if (qualityBadge) {
    qualityBadge.className = "badge badge-bad";
    qualityBadge.textContent = "Sin conexión";
  }
  setText("qualitySignals", PLACEHOLDER.CONNECTION_ERROR);
  setText("qualityOutcomes", PLACEHOLDER.CONNECTION_ERROR);
  setText("qualityMetrics", PLACEHOLDER.CONNECTION_ERROR);
  setText("qualityReasons", "No fue posible leer cobertura ni frescura de datasets.");
  toggleEmptyState("qualityReasons", false);

  document.querySelectorAll(".context-pill").forEach((el) => {
    el.classList.add("no-data");
  });

  setText("kpiHealth", PLACEHOLDER.CONNECTION_ERROR);
  setText("kpiSignals", PLACEHOLDER.NO_DATA);
  setText("kpiLong", PLACEHOLDER.NO_DATA);
  setText("kpiShort", PLACEHOLDER.NO_DATA);
  setText("kpiIgnored", PLACEHOLDER.NO_DATA);
  setText("kpiBlocked", PLACEHOLDER.NO_DATA);
  setText("kpiApis", PLACEHOLDER.CONNECTION_ERROR);
  setText("kpiLastSignal", PLACEHOLDER.ND);

  setText("kpiWinrate", PLACEHOLDER.ND);
  setText("kpiExpectancy", PLACEHOLDER.ND);
  setText("kpiPrecision", PLACEHOLDER.ND);
  setText("kpiDrawdown", PLACEHOLDER.ND);
  setText("kpiSample", PLACEHOLDER.NO_DATA);

  const longBody = document.getElementById("topLongBody");
  if (longBody) {
    longBody.innerHTML = '<tr class="empty-row"><td colspan="8">Error de conexión<span class="empty-row-note">No se pudieron cargar señales alcistas.</span></td></tr>';
  }
  const shortBody = document.getElementById("topShortBody");
  if (shortBody) {
    shortBody.innerHTML = '<tr class="empty-row"><td colspan="8">Error de conexión<span class="empty-row-note">No se pudieron cargar señales bajistas.</span></td></tr>';
  }
}

function getSignalScore(row) {
  if (!row) return 0;
  return row.decision === "SHORT_SETUP" ? Number(row.short_score || 0) : Number(row.long_score || 0);
}

function getRisk(row) {
  if (!row) {
    return { label: "Riesgo medio", cls: "risk-medium" };
  }
  const confidence = Number(row.confidence || 0);
  const penalties = Number(row.reasons?.penalties || 0);
  const hasVetoReasons = Array.isArray(row.reasons?.veto_reasons) && row.reasons.veto_reasons.length > 0;

  if (hasVetoReasons || confidence < 0.62 || penalties > 8) {
    return { label: "Riesgo alto", cls: "risk-high" };
  }
  if (confidence < 0.75 || penalties > 4) {
    return { label: "Riesgo medio", cls: "risk-medium" };
  }
  return { label: "Riesgo bajo", cls: "risk-low" };
}

function reasonLabel(key) {
  const dict = {
    momentum: "Momentum fuerte",
    technical_structure: "Estructura técnica",
    volume_acceleration: "Volumen acelerando",
    liquidity_quality: "Liquidez sólida",
    wallet_flow: "Flujo wallets",
    overextension: "Sobreextensión",
    distribution_signal: "Distribución",
    momentum_loss: "Pérdida de momentum",
    market_risk_off: "Contexto defensivo",
  };
  return dict[key] || key;
}

function extractReasons(row) {
  if (!row) {
    return ["Sin detalle"];
  }
  const pos = Array.isArray(row.reasons?.top_positive) ? row.reasons.top_positive : [];
  const risk = Array.isArray(row.reasons?.top_risks) ? row.reasons.top_risks : [];

  const merged = [...pos.slice(0, 2), ...risk.slice(0, 1)]
    .map((item) => reasonLabel(item[0]))
    .slice(0, 3);

  if (merged.length === 0) {
    return ["Sin detalle"];
  }
  return merged;
}

function renderSignalTable(bodyId, rows, normalizedQuery = "") {
  const body = document.getElementById(bodyId);
  body.innerHTML = "";
  const safeRows = asArray(rows).filter((row) => rowMatchesSignalQuery(row, normalizedQuery) && rowMatchesUiFilters(row));

  if (safeRows.length === 0) {
    body.innerHTML = '<tr class="empty-row"><td colspan="9">Sin datos<span class="empty-row-note">No hay señales activas para este bloque.</span></td></tr>';
    return;
  }

  safeRows.forEach((row) => {
    const identity = identityFromRow(row);
    const tr = document.createElement("tr");
    const risk = getRisk(row);
    const reasons = extractReasons(row)
      .map((r) => `<span class="reason-badge">${r}</span>`)
      .join("");
    const operabilityStatus = String(row?.operability_status || "watchlist").toLowerCase();

    tr.className = identity.isUncertain ? "row-uncertain" : "";
    tr.innerHTML = `
      <td>
        <span class="token-name ${identity.isUncertain ? "token-name-uncertain" : ""}">${identity.symbol}</span>
        <span class="token-sub">${identity.name}</span>
        <span class="token-sub">${identity.shortAddress}</span>
        <div class="identity-badges">${renderMetaBadges(identity)}</div>
      </td>
      <td>${identity.chain}</td>
      <td>${fmtNum(getSignalScore(row), 1)}</td>
      <td>${fmtNum(row?.confidence ?? 0, 2)}</td>
      <td><span class="risk-badge ${risk.cls}">${risk.label}</span></td>
      <td><span class="${operabilityClass(operabilityStatus)}">${operabilityLabel(operabilityStatus)}</span></td>
      <td>${fmtTime(row?.ts)}</td>
      <td><div class="reason-wrap">${reasons}</div></td>
      <td>
        <div class="actions">
          <button class="link-btn" data-action="detail" data-token="${row.token_address}">Ver detalle</button>
          <a class="link-btn" href="/token?address=${encodeURIComponent(row.token_address)}">Ver gráfico</a>
          <button class="link-btn" data-action="risk" data-token="${row.token_address}">Ver riesgo</button>
        </div>
      </td>
    `;

    body.appendChild(tr);
  });
}

function renderOperableCandidates(rows, normalizedQuery = "") {
  const body = document.getElementById("operableCandidatesBody");
  if (!body) return;

  const candidates = asArray(rows)
    .filter((row) => {
      const identity = identityFromRow(row);
      const status = String(row?.operability_status || "").toLowerCase();
      return (
        status === "operable"
        && rowMatchesSignalQuery(row, normalizedQuery)
        && rowMatchesUiFilters(row)
        && !identity.metadataIsFallback
        && ["confirmed", "inferred"].includes(identity.metadataConfidence)
      );
    })
    .sort((a, b) => Number(getSignalScore(b)) - Number(getSignalScore(a)))
    .slice(0, 12);

  body.innerHTML = "";

  if (candidates.length === 0) {
    body.innerHTML = '<tr class="empty-row"><td colspan="8">Sin candidatas operables<span class="empty-row-note">El modelo puede ver señales, pero ninguna cumple tradeability real ahora.</span></td></tr>';
    toggleEmptyState("emptyOperable", false);
    return;
  }

  toggleEmptyState("emptyOperable", true);
  candidates.forEach((row) => {
    const identity = identityFromRow(row);
    const risk = getRisk(row);
    const setup = row.decision === "SHORT_SETUP" ? "SHORT" : "LONG";
    const operabilityReason = row.operability_reason || "Cumple filtros operativos";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <span class="token-name">${identity.symbol}</span>
        <span class="token-sub">${identity.name}</span>
        <span class="token-sub">${identity.shortAddress}</span>
      </td>
      <td>${identity.chain}</td>
      <td>${setup}</td>
      <td>${fmtNum(getSignalScore(row), 1)}</td>
      <td>${fmtNum(row?.confidence ?? 0, 2)}</td>
      <td><span class="risk-badge ${risk.cls}">${risk.label}</span></td>
      <td><span class="${operabilityClass("operable")}">${operabilityLabel("operable")}</span></td>
      <td>${operabilityReason}</td>
    `;
    body.appendChild(tr);
  });
}

function buildExecutiveSummary(health, latest, longRows, shortRows) {
  const safeLatest = asArray(latest);
  const safeLongRows = asArray(longRows);
  const safeShortRows = asArray(shortRows);
  const backendHealthy = health.status === "ok";
  const longCount = safeLatest.filter((x) => x.decision === "LONG_SETUP").length;
  const shortCount = safeLatest.filter((x) => x.decision === "SHORT_SETUP").length;
  const biasRatio = longCount - shortCount;

  let bias = "Neutral";
  if (biasRatio > 3) bias = "Long";
  if (biasRatio < -3) bias = "Short";

  const riskScores = safeLatest.map((x) => getRisk(x).label);
  const highRisk = riskScores.filter((x) => x === "Riesgo alto").length;
  const mediumRisk = riskScores.filter((x) => x === "Riesgo medio").length;

  let marketRisk = "Bajo";
  if (highRisk > Math.max(2, safeLatest.length * 0.25)) marketRisk = "Alto";
  else if (mediumRisk > Math.max(2, safeLatest.length * 0.35)) marketRisk = "Medio";

  const bestLong = safeLongRows[0] ? `${identityFromRow(safeLongRows[0]).symbol} (${fmtNum(safeLongRows[0].long_score, 1)})` : PLACEHOLDER.NO_DATA;
  const bestShort = safeShortRows[0] ? `${identityFromRow(safeShortRows[0]).symbol} (${fmtNum(safeShortRows[0].short_score, 1)})` : PLACEHOLDER.NO_DATA;

  const motive =
    bias === "Long"
      ? "Motivo: predominan setups alcistas con mejor consistencia y menor nivel de riesgo relativo."
      : bias === "Short"
      ? "Motivo: aumentan setups bajistas y el mercado muestra mayor fragilidad en los últimos ciclos."
      : "Motivo: equilibrio entre setups alcistas y bajistas, sin ventaja clara de dirección.";

  let globalStatus = "Operativo";
  if (!backendHealthy) {
    globalStatus = "Error";
  } else if (safeLatest.length === 0) {
    globalStatus = "Degradado";
  } else if (safeLongRows.length === 0 || safeShortRows.length === 0) {
    globalStatus = "Degradado";
  }

  return { globalStatus, bias, marketRisk, bestLong, bestShort, motive };
}

function ExecutiveCard(summary) {
  setText("execBias", summary.bias);
  setText("execRisk", summary.marketRisk);
  setText("execBestLong", summary.bestLong);
  setText("execBestShort", summary.bestShort);
  setText("execReason", summary.motive);
  setGlobalStatus(summary.globalStatus);
}

function normalizeTrend(value) {
  if (!value) return PLACEHOLDER.ND;
  const map = {
    alcista: "Alcista",
    bajista: "Bajista",
    neutral: "Neutral",
    caliente: "Caliente",
    frio: "Frio",
    "frío": "Frio",
    normal: "Normal",
    alta: "Alta",
    media: "Media",
    baja: "Baja",
  };
  return map[String(value).toLowerCase()] || value;
}

function MarketContextBar(context) {
  const hasContext = context && typeof context === "object" && context.status;

  setText("ctxBtc", hasContext ? normalizeTrend(context.btc_trend) : PLACEHOLDER.ND);
  setText("ctxSol", hasContext ? normalizeTrend(context.sol_trend) : PLACEHOLDER.ND);
  setText("ctxMeme", hasContext ? normalizeTrend(context.meme_regime) : PLACEHOLDER.ND);
  setText("ctxLiq", hasContext ? normalizeTrend(context.market_liquidity) : PLACEHOLDER.ND);
  setText("ctxFreshness", `Fuente: ${hasContext ? context.source_freshness || "N/D" : "N/D"}`);
  setText(
    "ctxConfidence",
    `Confianza: ${hasContext && Number.isFinite(Number(context.confidence)) ? `${Math.round(Number(context.confidence) * 100)} %` : "N/D"}`
  );

  toggleEmptyState("contextEmpty", !hasContext);
  document.querySelectorAll(".context-pill").forEach((el) => {
    el.classList.toggle("no-data", !hasContext);
  });
}

function formatQualityDataset(ds) {
  if (!ds || typeof ds !== "object") return PLACEHOLDER.ND;
  const freshness = ds.freshness || "sin datos";
  const count = Number.isFinite(Number(ds.count)) ? Number(ds.count) : 0;
  const mins = Number.isFinite(Number(ds.minutes_ago)) ? `${Number(ds.minutes_ago).toFixed(1)} min` : "N/D";
  return `${freshness} | n=${count} | ${mins}`;
}

function DataQualityCard(quality) {
  const badge = document.getElementById("qualityBadge");
  const hasQuality = quality && typeof quality === "object" && quality.status;

  if (!hasQuality) {
    if (badge) {
      badge.className = "badge badge-info";
      badge.textContent = PLACEHOLDER.ND;
    }
    setText("qualitySignals", PLACEHOLDER.ND);
    setText("qualityOutcomes", PLACEHOLDER.ND);
    setText("qualityMetrics", PLACEHOLDER.ND);
    setText("qualityReasons", "Sin datos de calidad de datasets.");
    toggleEmptyState("qualityReasons", false);
    return;
  }

  if (badge) {
    badge.className = "badge";
    if (quality.status === "ok") {
      badge.classList.add("badge-ok");
      badge.textContent = "OK";
    } else {
      badge.classList.add("badge-warn");
      badge.textContent = "Degradado";
    }
  }

  setText("qualitySignals", formatQualityDataset(quality.datasets?.signals));
  setText("qualityOutcomes", formatQualityDataset(quality.datasets?.outcomes));
  setText("qualityMetrics", formatQualityDataset(quality.datasets?.metrics));

  const reasons = asArray(quality.degraded_reasons);
  if (reasons.length > 0) {
    setText("qualityReasons", `Alertas: ${reasons.join("; ")}`);
    toggleEmptyState("qualityReasons", false);
  } else {
    toggleEmptyState("qualityReasons", true);
  }
}

function InsightsPanel(summary, metricsLive, latest) {
  const list = document.getElementById("insightsList");
  list.innerHTML = "";
  const safeLatest = asArray(latest);

  const insightA =
    summary.bias === "Long"
      ? "El sistema detecta mayor cantidad de oportunidades alcistas que bajistas en la ventana reciente."
      : summary.bias === "Short"
      ? "El sistema detecta mayor presión bajista y recomienda priorizar escenarios defensivos."
      : "No hay sesgo dominante; conviene operar selectivamente y con riesgo contenido.";

  const insightB =
    metricsLive.status === "insufficient_data"
      ? "Aún no hay suficiente histórico para validar rendimiento reciente con confianza estadística."
      : Number(metricsLive.expectancy) >= 0
      ? "Las mejores señales recientes mantienen expectativa positiva por operación."
      : "La expectativa reciente es negativa; priorizar calidad de setup sobre frecuencia.";

  const blocked = safeLatest.filter((x) => x.veto).length;
  const insightC =
    blocked > 0
      ? `Se bloquearon ${blocked} señales por riesgo o flags de seguridad en la última muestra.`
      : "No se detectaron bloqueos por seguridad en la última muestra analizada.";

  const offlineInsights = [
    "El panel no pudo actualizar datos en tiempo real.",
    "Cuando la API vuelva a responder, esta sección resumirá sesgo y calidad de señales.",
    "Mientras tanto, se mantiene visible la estructura con los últimos datos válidos.",
  ];

  const selectedInsights = STATE.globalStatus === "Sin conexión" ? offlineInsights : [insightA, insightB, insightC];

  selectedInsights.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
  });
}

function MetricCard(metricsLive) {
  if (metricsLive.status === "insufficient_data") {
    setText("kpiWinrate", PLACEHOLDER.ND);
    setText("kpiExpectancy", PLACEHOLDER.ND);
    setText("kpiPrecision", PLACEHOLDER.ND);
    setText("kpiDrawdown", PLACEHOLDER.ND);
    setText("kpiSample", PLACEHOLDER.NO_DATA);
    toggleEmptyState("performanceEmpty", true);
    return;
  }

  toggleEmptyState("performanceEmpty", false);

  setText("kpiWinrate", fmtPct(metricsLive.win_rate));
  setText("kpiExpectancy", fmtNum(metricsLive.expectancy, 2));
  setText("kpiPrecision", fmtPct(metricsLive.precision_top_decile));
  setText("kpiDrawdown", `${fmtNum(metricsLive.max_drawdown_proxy, 2)} %`);
  setText("kpiSample", `${metricsLive.n_signals}`);
}

function SystemCard(health, latest) {
  const safeLatest = asArray(latest);
  const now = Date.now();
  const in24h = safeLatest.filter((x) => x?.ts && now - new Date(x.ts).getTime() <= 24 * 60 * 60 * 1000);

  const longSetups = in24h.filter((x) => x.decision === "LONG_SETUP").length;
  const shortSetups = in24h.filter((x) => x.decision === "SHORT_SETUP").length;
  const ignored = in24h.filter((x) => x.decision === "IGNORE").length;
  const blocked = in24h.filter((x) => x.veto).length;

  setText("kpiHealth", health.status === "ok" ? "Operativo" : "Error");
  setText("kpiSignals", in24h.length > 0 ? `${in24h.length}` : PLACEHOLDER.NO_DATA);
  setText("kpiLong", in24h.length > 0 ? `${longSetups}` : PLACEHOLDER.NO_DATA);
  setText("kpiShort", in24h.length > 0 ? `${shortSetups}` : PLACEHOLDER.NO_DATA);
  setText("kpiIgnored", in24h.length > 0 ? `${ignored}` : PLACEHOLDER.NO_DATA);
  setText("kpiBlocked", in24h.length > 0 ? `${blocked}` : PLACEHOLDER.NO_DATA);
  setText("kpiApis", health.status === "ok" ? "Operativas" : PLACEHOLDER.CONNECTION_ERROR);
  setText("kpiLastSignal", safeLatest[0]?.ts ? fmtTime(safeLatest[0].ts) : PLACEHOLDER.NO_DATA);
}

function renderOutcomesChart(rows) {
  const safeRows = asArray(rows);
  const ctx = document.getElementById("outcomesChart");
  const sliced = safeRows
    .filter((r) => Number.isFinite(Number(r?.ret_pct)))
    .slice(0, 40)
    .reverse();
  const labels = sliced.map((r, i) => `${r.horizon} #${i + 1}`);
  const values = sliced.map((r) => Number(r.ret_pct));

  if (outcomesChart) {
    outcomesChart.destroy();
    outcomesChart = undefined;
  }

  const hasData = sliced.length > 0;
  toggleEmptyState("outcomesEmpty", !hasData);

  if (!hasData) {
    const context = ctx?.getContext("2d");
    if (context && ctx) {
      context.clearRect(0, 0, ctx.width, ctx.height);
    }
    return;
  }

  outcomesChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Retorno de señal (%)",
          data: values,
          backgroundColor: values.map((v) => (v >= 0 ? "rgba(47,214,181,0.72)" : "rgba(255,111,111,0.72)")),
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#8ea5b3" } },
      },
      scales: {
        y: {
          ticks: { color: "#8ea5b3", callback: (v) => `${v}%` },
          grid: { color: "rgba(255,255,255,0.08)" },
        },
        x: { ticks: { color: "#8ea5b3", maxRotation: 0 }, grid: { display: false } },
      },
    },
  });
}

function renderMetricsChart(rows) {
  const safeRows = asArray(rows);
  const ctx = document.getElementById("metricsChart");
  const filtered = safeRows
    .filter((r) => r.horizon === "4h" && Number.isFinite(Number(r?.win_rate)) && Number.isFinite(Number(r?.expectancy)))
    .slice(0, 24)
    .reverse();
  const labels = filtered.map((r) => new Date(r.ts).toLocaleDateString());
  const win = filtered.map((r) => Number(r.win_rate) * 100);
  const exp = filtered.map((r) => Number(r.expectancy));

  if (metricsChart) {
    metricsChart.destroy();
    metricsChart = undefined;
  }

  const hasData = filtered.length > 0;
  toggleEmptyState("metricsEmpty", !hasData);

  if (!hasData) {
    const context = ctx?.getContext("2d");
    if (context && ctx) {
      context.clearRect(0, 0, ctx.width, ctx.height);
    }
    return;
  }

  metricsChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Tasa de acierto (%)",
          data: win,
          borderColor: "#2fd6b5",
          backgroundColor: "rgba(47,214,181,0.15)",
          yAxisID: "y",
          tension: 0.2,
          pointRadius: 2,
        },
        {
          label: "Ganancia esperada",
          data: exp,
          borderColor: "#f2b84b",
          backgroundColor: "rgba(242,184,75,0.15)",
          yAxisID: "y1",
          tension: 0.2,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#8ea5b3" } } },
      scales: {
        y: {
          position: "left",
          ticks: { color: "#8ea5b3", callback: (v) => `${v}%` },
          grid: { color: "rgba(255,255,255,0.08)" },
        },
        y1: {
          position: "right",
          ticks: { color: "#8ea5b3" },
          grid: { drawOnChartArea: false },
        },
        x: { ticks: { color: "#8ea5b3" }, grid: { display: false } },
      },
    },
  });
}

async function TokenDetailDrawer(tokenAddress) {
  const drawer = document.getElementById("tokenDrawer");
  drawer.classList.add("open");

  setText("drawerTitle", `Detalle ${shortAddr(tokenAddress)}`);
  setText("drawerSubtitle", "Cargando información de señal...");

  try {
    const [explain, historyResp, scannerSignals] = await Promise.all([
      getJson(`/tokens/${encodeURIComponent(tokenAddress)}/explain`),
      getJson(`/tokens/${encodeURIComponent(tokenAddress)}/history?limit=80`),
      getJsonSafe(`/scanner/token/${encodeURIComponent(tokenAddress)}/signals`),
    ]);
    const history = asArray(historyResp);

    const risk = getRisk(explain);
    const identity = identityFromRow(explain);

    setText("drawerTitle", identity.symbol);
    setText("drawerSubtitle", identity.name);
    setText("dName", identity.name);
    setText("dSymbol", identity.symbol);
    setText("dAddressFull", identity.address || PLACEHOLDER.ND);
    setText("dChain", identity.chain || PLACEHOLDER.ND);
    setText("dPair", identity.principalPair || PLACEHOLDER.ND);
    setText("dLong", fmtNum(explain.long_score, 1));
    setText("dShort", fmtNum(explain.short_score, 1));
    setText("dConf", fmtNum(explain.confidence, 2));
    setText("dRisk", risk.label);
    setText("dLiq", "N/D");
    setText("dVol1h", "N/D");
    setText("dMetaSource", metadataSourceLabel(identity.metadataSource));
    setText("dMetaConfidence", metadataConfidenceLabel(identity.metadataConfidence));
    setText("dMetaFallback", identity.metadataIsFallback ? "Fallback" : "Real");
    setText("dMetaLastSource", metadataSourceLabel(identity.metadataLastSource));
    setText("dLastValidated", fmtTime(identity.metadataLastValidatedAt || explain.metadata_last_validated_at || explain.ts));
    setText("dMetaConflict", identity.metadataConflict ? "Sí" : "No");

    const flags = Array.isArray(explain.reasons?.veto_reasons) && explain.reasons.veto_reasons.length
      ? explain.reasons.veto_reasons.join(", ")
      : "Sin flags graves";
    setText("dFlags", flags);
    setText("dTs", fmtTime(explain.ts));

    const reasons = extractReasons(explain).join(" | ");
    setText("dReasonText", `La señal fue rankeada por: ${reasons}.`);

    const composite = scannerSignals?.signals_snapshot?.composite || scannerSignals?.signal_dimensions?.composite || {};
    const social = scannerSignals?.signals_snapshot?.social || scannerSignals?.signal_dimensions?.social || {};
    const breakout = scannerSignals?.signals_snapshot?.breakout || scannerSignals?.signal_dimensions?.breakout || {};
    setText("dWhale", fmtNum(composite.whale_accumulation_score || 0, 1));
    setText("dSocial", fmtNum(composite.social_momentum_score || 0, 1));
    setText("dDemand", fmtNum(composite.demand_quality_score || 0, 1));
    setText("dNarrative", fmtNum(composite.narrative_strength_score || 0, 1));
    setText("dBreakout", fmtNum(composite.breakout_timing_score || 0, 1));
    setText("dSpecMomentum", fmtNum(composite.speculative_momentum_score || 0, 1));
    setText("dBotSuspicion", fmtNum(social.bot_suspicion_score || 0, 1));
    setText("dOverextension", fmtNum(breakout.overextension_penalty || 0, 1));
    setText("dSignalExplain", buildSignalExplainability(scannerSignals));

    const copyBtn = document.getElementById("copyAddressBtn");
    if (copyBtn) {
      copyBtn.setAttribute("data-address", identity.address);
      copyBtn.textContent = "Copiar address";
    }

    const birdeye = document.getElementById("openBirdeyeLink");
    if (birdeye) {
      birdeye.href = `https://birdeye.so/token/${encodeURIComponent(identity.address)}?chain=${encodeURIComponent(identity.chain)}`;
    }

    const dex = document.getElementById("openDexLink");
    if (dex) {
      const dexTarget = identity.principalPair || identity.address;
      dex.href = `https://dexscreener.com/${encodeURIComponent(identity.chain)}/${encodeURIComponent(dexTarget)}`;
    }

    const solscan = document.getElementById("openSolscanLink");
    if (solscan) {
      solscan.href = `https://solscan.io/token/${encodeURIComponent(identity.address)}`;
    }

    const entry = Number(explain.entry_price || 0);
    if (entry > 0) {
      const invalid = explain.decision === "SHORT_SETUP" ? entry * 1.06 : entry * 0.94;
      const tp = explain.decision === "SHORT_SETUP" ? entry * 0.9 : entry * 1.12;
      setText("dEntry", entry.toFixed(8));
      setText("dInvalid", invalid.toFixed(8));
      setText("dTp", tp.toFixed(8));
    } else {
      setText("dEntry", "N/D");
      setText("dInvalid", "N/D");
      setText("dTp", "N/D");
    }

    const chartCtx = document.getElementById("tokenHistoryChart");
    const hist = [...history].reverse();
    const labels = hist.map((r) => fmtTime(r.ts));
    const longData = hist.map((r) => Number(r.long_score));
    const shortData = hist.map((r) => Number(r.short_score));

    if (tokenHistoryChart) tokenHistoryChart.destroy();
    tokenHistoryChart = new Chart(chartCtx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Score alcista",
            data: longData,
            borderColor: "#2fd6b5",
            tension: 0.2,
            pointRadius: 1,
          },
          {
            label: "Score bajista",
            data: shortData,
            borderColor: "#f2b84b",
            tension: 0.2,
            pointRadius: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#8ea5b3" } } },
        scales: {
          y: { ticks: { color: "#8ea5b3" }, grid: { color: "rgba(255,255,255,0.08)" } },
          x: { ticks: { color: "#8ea5b3", maxTicksLimit: 8 }, grid: { display: false } },
        },
      },
    });
  } catch (e) {
    setText("drawerSubtitle", "No se pudo cargar el detalle del token.");
  }
}

function bindTableActions() {
  document.querySelectorAll("[data-action='detail'], [data-action='risk']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const token = btn.getAttribute("data-token");
      await TokenDetailDrawer(token);
    });
  });
}

function bindIdentityActions() {
  const copyBtn = document.getElementById("copyAddressBtn");
  if (!copyBtn) {
    return;
  }

  copyBtn.addEventListener("click", async () => {
    const address = copyBtn.getAttribute("data-address") || "";
    if (!address) {
      return;
    }
    try {
      await navigator.clipboard.writeText(address);
      copyBtn.textContent = "Mint copiado";
    } catch (_e) {
      copyBtn.textContent = "No se pudo copiar";
    }
  });
}

function categoryClass(category) {
  if (category === "LONG ahora") return "cat-long";
  if (category === "WATCHLIST prioritaria") return "cat-watch-priority";
  if (category === "WATCHLIST secundaria") return "cat-watch-secondary";
  if (category === "SHORT solo paper") return "cat-short-paper";
  if (category === "NO TRADE") return "cat-no-trade";
  return "cat-ignore";
}

function flattenWatchlist(data) {
  const strong = asArray(data?.strong);
  const priority = asArray(data?.priority);
  const secondary = asArray(data?.secondary);
  const shortPaper = asArray(data?.short_paper);
  return [...strong, ...priority, ...secondary, ...shortPaper]
    .sort((a, b) => Number(a.rank || 0) - Number(b.rank || 0));
}

function renderWatchlistTable(payload) {
  const body = document.getElementById("watchlistBody");
  if (!body) return;

  const rows = flattenWatchlist(payload).filter((row) => {
    const identity = identityFromRow(row);
    const status = String(row?.operability_status || "watchlist").toLowerCase();
    const risk = String(row?.risk_label || "").toLowerCase();

    if (STATE.hideFallback && (identity.metadataIsFallback || ["fallback", "unverified"].includes(identity.metadataConfidence))) {
      return false;
    }
    if (STATE.operabilityFilter && status !== STATE.operabilityFilter) {
      return false;
    }
    if (STATE.riskFilter) {
      const map = { low: "bajo", medium: "medio", high: "alto" };
      const wanted = map[STATE.riskFilter] || "";
      if (wanted && risk !== wanted) {
        return false;
      }
    }
    return true;
  });
  body.innerHTML = "";
  if (rows.length === 0) {
    body.innerHTML = '<tr class="empty-row"><td colspan="14">Sin entradas<span class="empty-row-note">Todavía no hay watchlist para hoy.</span></td></tr>';
    toggleEmptyState("watchlistEmpty", false);
    return;
  }

  toggleEmptyState("watchlistEmpty", true);
  rows.forEach((row) => {
    const identity = identityFromRow(row);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="token-name">${identity.shortAddress}</span><span class="token-sub">${identity.symbol} · ${identity.name}</span><div class="identity-badges">${renderMetaBadges(identity)}</div></td>
      <td><span class="category-pill ${categoryClass(row.category)}">${row.category}</span></td>
      <td><span class="${operabilityClass(row.operability_status || "watchlist")}">${operabilityLabel(row.operability_status || "watchlist")}</span></td>
      <td>${fmtNum(Math.max(Number(row.score_long || 0), Number(row.score_short || 0)), 1)}</td>
      <td>${fmtNum(row.confidence || 0, 2)}</td>
      <td><span class="risk-badge ${row.risk_label === "bajo" ? "risk-low" : row.risk_label === "alto" ? "risk-high" : "risk-medium"}">${row.risk_label}</span></td>
      <td>${fmtNum(row.liquidity_usd || 0, 0)}</td>
      <td>${fmtNum(row.whale_accumulation_score || 0, 1)}</td>
      <td>${fmtNum(row.social_momentum_score || 0, 1)}</td>
      <td>${fmtNum(row.demand_quality_score || 0, 1)}</td>
      <td>${fmtNum(row.narrative_strength_score || 0, 1)}</td>
      <td>${fmtNum(row.breakout_timing_score || 0, 1)}</td>
      <td>${fmtTime(row.ts)}</td>
      <td>${row.main_reason || "-"}</td>
    `;
    body.appendChild(tr);
  });
}

function formatTopDimensionList(rows, scoreKey) {
  const list = asArray(rows)
    .slice(0, 3)
    .map((x) => `${shortAddr(x.token_address)} (${fmtNum(x[scoreKey] || 0, 1)})`);
  return list.length ? list.join(" | ") : "Sin datos";
}

function renderDimensionLeaders(whales, social, demand, breakouts, watchlistPayload) {
  setText("topWhalesList", formatTopDimensionList(whales?.rows, "whale_accumulation_score"));
  setText("topSocialList", formatTopDimensionList(social?.rows, "social_velocity_score"));
  setText("topBreakoutsList", formatTopDimensionList(breakouts?.rows, "breakout_setup_score"));

  const demandRows = asArray(demand?.rows).map((x) => ({
    token_address: x.token_address,
    demand_quality_score: x.transaction_demand_score,
  }));
  const fallbackRows = flattenWatchlist(watchlistPayload)
    .slice()
    .sort((a, b) => Number(b.demand_quality_score || 0) - Number(a.demand_quality_score || 0));
  setText("topDemandList", formatTopDimensionList(demandRows.length ? demandRows : fallbackRows, "demand_quality_score"));
}

function buildSignalExplainability(scannerSignals) {
  if (!scannerSignals) {
    return "Sin snapshot de señales por dimensión para este token.";
  }
  const composite = scannerSignals?.signals_snapshot?.composite || scannerSignals?.signal_dimensions?.composite || {};
  const social = scannerSignals?.signals_snapshot?.social || scannerSignals?.signal_dimensions?.social || {};
  const demand = scannerSignals?.signals_snapshot?.demand || scannerSignals?.signal_dimensions?.demand || {};
  const breakout = scannerSignals?.signals_snapshot?.breakout || scannerSignals?.signal_dimensions?.breakout || {};

  if ((demand.transaction_demand_score || 0) < 40) {
    return "Se penaliza por demanda transaccional débil, aunque pueda haber narrativa o social activo.";
  }
  if ((social.bot_suspicion_score || 0) > 62 && (social.social_wallet_divergence_score || 0) > 30) {
    return "Se penaliza por hype social con sospecha de bots y divergencia frente al flujo on-chain.";
  }
  if ((breakout.overextension_penalty || 0) > 38) {
    return "Se mantiene cautela por sobreextensión post-ruptura; mejor esperar reentrada de menor riesgo.";
  }
  if ((composite.speculative_momentum_score || 0) >= 58) {
    return "Sube prioridad por combinación de wallets, demanda real y timing de ruptura razonable.";
  }
  return "Se mantiene en seguimiento por señales mixtas; falta confirmación adicional de flujo y timing.";
}

function renderDiscardedTable(payload) {
  const body = document.getElementById("discardedBody");
  if (!body) return;

  const rows = asArray(payload?.rows);
  body.innerHTML = "";
  if (rows.length === 0) {
    body.innerHTML = '<tr class="empty-row"><td colspan="5">Sin descartes<span class="empty-row-note">No hay tokens descartados hoy.</span></td></tr>';
    toggleEmptyState("discardedEmpty", false);
    return;
  }

  toggleEmptyState("discardedEmpty", true);
  rows.slice(0, 25).forEach((row) => {
    const identity = identityFromRow(row);
    const activeFlags = Object.entries(row.flags || {})
      .filter(([, value]) => Boolean(value))
      .map(([key]) => `<span class="flag-chip">${key}</span>`)
      .join("");

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="token-name">${identity.shortAddress}</span><span class="token-sub">${identity.symbol} · ${identity.name}</span><div class="identity-badges">${renderMetaBadges(identity)}</div></td>
      <td><span class="category-pill ${categoryClass(row.category)}">${row.category}</span><div class="token-sub"><span class="${operabilityClass(row.operability_status || "bloqueado")}">${operabilityLabel(row.operability_status || "bloqueado")}</span></div></td>
      <td>${row.discard_reason || "-"}</td>
      <td><div class="flags-wrap">${activeFlags || '<span class="flag-chip">sin flags</span>'}</div></td>
      <td>${fmtTime(row.ts)}</td>
    `;
    body.appendChild(tr);
  });
}

function renderFunnel(funnel) {
  setText("funnelDetected", funnel?.steps?.birdeye_detected ?? 0);
  setText("funnelValidated", funnel?.steps?.dex_validated ?? 0);
  setText("funnelRanked", funnel?.steps?.classified ?? 0);
  setText("funnelBlockedIdentity", funnel?.steps?.blocked_identity ?? 0);
  setText("funnelBlockedRisk", funnel?.steps?.blocked_risk ?? 0);
  setText("funnelDegradedQuality", funnel?.steps?.degraded_quality ?? 0);
  setText("funnelWatchlist", funnel?.steps?.watchlist ?? 0);
  setText("funnelOperable", funnel?.steps?.operable ?? 0);
  setText("funnelWatchlistOnly", funnel?.steps?.watchlist_only ?? 0);
  setText("funnelNoTrade", funnel?.steps?.no_trade ?? 0);
}

function renderPlaybookStatus(status, funnel, watchlist, discarded) {
  const latest = status?.latest || {};
  const sources = latest.sources || {};
  const sourceSummary = [sources.birdeye || "-", sources.dexscreener || "-", sources.dashboard_scores || "-"]
    .join(" | ");

  setText("playbookLastScan", latest.finished_at ? fmtTime(latest.finished_at) : (latest.started_at ? fmtTime(latest.started_at) : "N/D"));
  setText("playbookSources", sourceSummary);
  setText("playbookProcessed", latest.processed ?? 0);
  setText("playbookWatchlistCount", latest.watchlist ?? 0);
  setText("playbookQualityState", latest.degraded ? "Degradada" : "OK");
  setText("playbookCompleteness", latest.status || "empty");

  const badge = document.getElementById("playbookRunState");
  if (badge) {
    badge.className = "badge";
    if (status?.running) {
      badge.classList.add("badge-info");
      badge.textContent = "Running";
    } else if (latest.status === "completed" && !latest.degraded) {
      badge.classList.add("badge-ok");
      badge.textContent = "Completo";
    } else if (latest.status === "completed" && latest.degraded) {
      badge.classList.add("badge-warn");
      badge.textContent = "Degradado";
    } else if (latest.status === "failed") {
      badge.classList.add("badge-bad");
      badge.textContent = "Fallido";
    } else {
      badge.classList.add("badge-info");
      badge.textContent = "N/D";
    }
  }

  const detected = Number(funnel?.steps?.birdeye_detected || 0);
  const validated = Number(funnel?.steps?.dex_validated || 0);
  const watchCount = Number(funnel?.steps?.watchlist || 0);
  const discardedCount = Number(funnel?.steps?.discarded || 0) || Number(discarded?.total || 0);
  setText("discDetected", detected);
  setText("discSurvived", validated);
  setText("discDiscarded", discardedCount);
  setText("discWatchlist", watchCount || Number(watchlist?.total || 0));
}

async function renderScannerBlocks() {
  const scannerQuery = STATE.signalQuery ? `q=${encodeURIComponent(STATE.signalQuery)}` : "";
  const scannerIdentity = STATE.scannerIdentity ? `identity=${encodeURIComponent(STATE.scannerIdentity)}` : "";
  const scannerParams = [scannerQuery, scannerIdentity].filter(Boolean).join("&");
  const watchlistUrl = scannerParams ? `/scanner/watchlist/today?${scannerParams}` : "/scanner/watchlist/today";

  const [status, funnel, watchlist, discarded] = await Promise.all([
    getJsonSafe("/scanner/status"),
    getJsonSafe("/scanner/funnel/latest"),
    getJsonSafe(watchlistUrl),
    getJsonSafe("/scanner/discarded/today"),
  ]);

  const [whales, social, demand, breakouts] = await Promise.all([
    getJsonSafe("/scanner/whales/latest?limit=30"),
    getJsonSafe("/scanner/social/latest?limit=30"),
    getJsonSafe("/scanner/demand/latest?limit=30"),
    getJsonSafe("/scanner/breakouts/latest?limit=30"),
  ]);

  renderFunnel(funnel || { steps: {} });
  renderWatchlistTable(watchlist || {});
  renderDiscardedTable(discarded || {});
  renderDimensionLeaders(
    whales || { rows: [] },
    social || { rows: [] },
    demand || { rows: [] },
    breakouts || { rows: [] },
    watchlist || {}
  );
  renderPlaybookStatus(status || {}, funnel || {}, watchlist || {}, discarded || {});
}

async function refresh() {
  setLoading(true);
  toggleBackendDown(false);
  setGlobalStatus(PLACEHOLDER.LOADING);
  try {
    const querySuffix = STATE.signalQuery ? `&q=${encodeURIComponent(STATE.signalQuery)}` : "";
    const [
      healthResp,
      latestResp,
      topLongRawResp,
      topShortRawResp,
      outcomesResp,
      metricsLiveResp,
      metricsReportsResp,
      marketContextResp,
      qualityResp,
    ] = await Promise.all([
      getJson("/health"),
      getJson(`/signals/latest?limit=200${querySuffix}`),
      getJson(`/signals/top?decision=LONG_SETUP&limit=40${querySuffix}`),
      getJson(`/signals/top?decision=SHORT_SETUP&limit=40${querySuffix}`),
      getJson("/outcomes/latest?limit=200"),
      getJson("/metrics/live?horizon=4h"),
      getJson("/metrics/reports/latest?limit=80"),
      getJson("/market/context"),
      getJson("/quality/summary"),
    ]);

    await renderScannerBlocks();

    const health = healthResp && typeof healthResp === "object" ? healthResp : { status: "error" };
    const latest = asArray(latestResp);
    const topLongRaw = asArray(topLongRawResp);
    const topShortRaw = asArray(topShortRawResp);
    const outcomes = asArray(outcomesResp);
    const metricsLive = metricsLiveResp && typeof metricsLiveResp === "object" ? metricsLiveResp : { status: "insufficient_data" };
    const metricsReports = asArray(metricsReportsResp);
    const marketContext = marketContextResp && typeof marketContextResp === "object" ? marketContextResp : null;
    const quality = qualityResp && typeof qualityResp === "object" ? qualityResp : null;

    const topLong = dedupeByToken(topLongRaw).slice(0, 10);
    const topShort = dedupeByToken(topShortRaw).slice(0, 10);

    STATE.latest = latest;
    STATE.topLong = topLong;
    STATE.topShort = topShort;

    const summary = buildExecutiveSummary(health, latest, topLong, topShort);

    const hasPartialDataGap =
      metricsLive.status === "insufficient_data" ||
      outcomes.length === 0 ||
      metricsReports.length === 0 ||
      (quality && quality.status !== "ok") ||
      (marketContext && marketContext.status !== "ok");

    if (summary.globalStatus === "Operativo" && hasPartialDataGap) {
      summary.globalStatus = "Degradado";
    }

    ExecutiveCard(summary);
    MarketContextBar(marketContext);
    DataQualityCard(quality);
    InsightsPanel(summary, metricsLive, latest);
    SystemCard(health, latest);
    MetricCard(metricsLive);

    const normalizedQuery = normalizeSearch(STATE.signalQuery);
    const visibleLong = topLong.filter((row) => rowMatchesSignalQuery(row, normalizedQuery) && rowMatchesUiFilters(row));
    const visibleShort = topShort.filter((row) => rowMatchesSignalQuery(row, normalizedQuery) && rowMatchesUiFilters(row));

    renderOperableCandidates(latest, normalizedQuery);
    renderSignalTable("topLongBody", topLong, normalizedQuery);
    renderSignalTable("topShortBody", topShort, normalizedQuery);
    toggleEmptyState("emptyLong", visibleLong.length === 0);
    toggleEmptyState("emptyShort", visibleShort.length === 0);
    bindTableActions();

    renderOutcomesChart(outcomes);
    renderMetricsChart(metricsReports);

    STATE.lastValidTs = new Date();
    setText("lastUpdate", `Actualizado: ${fmtTime(new Date().toISOString())}`);
  } catch (e) {
    console.error(e);
    setGlobalStatus("Sin conexión");
    toggleBackendDown(true);
    clearUiForConnectionError();
    toggleEmptyState("emptyLong", true);
    toggleEmptyState("emptyShort", true);
    toggleEmptyState("performanceEmpty", true);
    toggleEmptyState("contextEmpty", true);
    toggleEmptyState("qualityReasons", false);
    toggleEmptyState("outcomesEmpty", true);
    toggleEmptyState("metricsEmpty", true);
    if (outcomesChart) {
      outcomesChart.destroy();
      outcomesChart = undefined;
    }
    if (metricsChart) {
      metricsChart.destroy();
      metricsChart = undefined;
    }

    setText("lastUpdate", PLACEHOLDER.CONNECTION_ERROR);
    const insights = document.getElementById("insightsList");
    insights.innerHTML = "";
    InsightsPanel({ bias: "Neutral" }, { status: "insufficient_data" }, []);
  } finally {
    setLoading(false);
  }
}

function bindSignalSearch() {
  const input = document.getElementById("signalSearchInput");
  const identityFilter = document.getElementById("scannerIdentityFilter");
  const operabilityFilter = document.getElementById("operabilityFilter");
  const riskFilter = document.getElementById("riskFilter");
  const hideFallbackFilter = document.getElementById("hideFallbackFilter");
  const searchBtn = document.getElementById("signalSearchBtn");
  const clearBtn = document.getElementById("signalSearchClear");
  if (!input || !searchBtn || !clearBtn || !identityFilter || !operabilityFilter || !riskFilter || !hideFallbackFilter) {
    return;
  }

  const triggerSearch = async () => {
    STATE.signalQuery = input.value.trim();
    STATE.scannerIdentity = identityFilter.value;
    STATE.operabilityFilter = String(operabilityFilter.value || "").trim().toLowerCase();
    STATE.riskFilter = String(riskFilter.value || "").trim().toLowerCase();
    STATE.hideFallback = Boolean(hideFallbackFilter.checked);
    await refresh();
  };

  input.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      await triggerSearch();
    }
  });

  searchBtn.addEventListener("click", triggerSearch);
  clearBtn.addEventListener("click", async () => {
    input.value = "";
    identityFilter.value = "";
    operabilityFilter.value = "";
    riskFilter.value = "";
    hideFallbackFilter.checked = false;
    STATE.signalQuery = "";
    STATE.scannerIdentity = "";
    STATE.operabilityFilter = "";
    STATE.riskFilter = "";
    STATE.hideFallback = false;
    await refresh();
  });

  identityFilter.addEventListener("change", async () => {
    STATE.scannerIdentity = identityFilter.value;
    await refresh();
  });

  operabilityFilter.addEventListener("change", async () => {
    STATE.operabilityFilter = String(operabilityFilter.value || "").trim().toLowerCase();
    await refresh();
  });

  riskFilter.addEventListener("change", async () => {
    STATE.riskFilter = String(riskFilter.value || "").trim().toLowerCase();
    await refresh();
  });

  hideFallbackFilter.addEventListener("change", async () => {
    STATE.hideFallback = Boolean(hideFallbackFilter.checked);
    await refresh();
  });
}

async function runPlaybookScan() {
  const btn = document.getElementById("runPlaybookBtn");
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = "Running...";
  try {
    const res = await fetch("/scanner/run", { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await refresh();
  } catch (e) {
    console.error(e);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run scan";
  }
}

document.getElementById("refreshBtn").addEventListener("click", refresh);
document.getElementById("runPlaybookBtn").addEventListener("click", runPlaybookScan);
document.getElementById("drawerClose").addEventListener("click", () => {
  document.getElementById("tokenDrawer").classList.remove("open");
});
document.getElementById("tokenDrawer").addEventListener("click", (e) => {
  if (e.target.id === "tokenDrawer") {
    e.currentTarget.classList.remove("open");
  }
});

bindIdentityActions();
bindSignalSearch();

refresh();
