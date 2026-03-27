function fmtMoney(v) {
  if (v === null || v === undefined) return "N/A";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (v >= 1) return `$${v.toFixed(2)}`;
  return `$${v.toFixed(6)}`;
}

function fmtNum(v, d = 2) {
  if (v === null || v === undefined) return "N/A";
  return Number(v).toFixed(d);
}

function fmtPct(v) {
  if (v === null || v === undefined) return "N/A";
  return `${Number(v).toFixed(2)}%`;
}

function fmtSignedPct(v) {
  if (v === null || v === undefined) return "N/A";
  const n = Number(v);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function valuationChipClass(label) {
  const map = { OK: "ok", WARN: "warn", RICH: "rich" };
  return map[label] || "";
}

function makeStat(label, value) {
  return `<article class="stat"><div class="label">${label}</div><div class="value">${value}</div></article>`;
}

function makeCard(item) {
  const valLabel = item.valuation_label || "N/A";
  const liqLabel = item.liquidity_label || "N/A";
  const thesis = (item.thesis || []).map((x) => `<li>${x}</li>`).join("");
  const risks = (item.risk_flags || []).map((x) => `<li>${x}</li>`).join("");
  const cgLink = `https://www.coingecko.com/en/coins/${item.coingecko_id}`;
  const valuationNote = item.valuation_note || "N/A";

  return `
    <article class="card">
      <div class="head">
        <div>
          <div class="title">${item.name} (${item.symbol})</div>
          <div class="sub">Sector: ${item.sector} · Rank: ${item.market_cap_rank ?? "N/A"}</div>
        </div>
      </div>
      <div class="chips">
        <span class="chip ${valuationChipClass(valLabel)}">估值: ${valLabel}</span>
        <span class="chip">流动性: ${liqLabel}</span>
      </div>
      <div class="sub" style="margin-top:8px;">估值口径: ${valuationNote}</div>
      <div class="grid">
        <div class="kv"><div class="k">Price</div><div class="v">${fmtMoney(item.price_usd)}</div></div>
        <div class="kv"><div class="k">Market Cap</div><div class="v">${fmtMoney(item.market_cap_usd)}</div></div>
        <div class="kv"><div class="k">FDV</div><div class="v">${fmtMoney(item.fdv_usd)}</div></div>
        <div class="kv"><div class="k">FDV/MCAP</div><div class="v">${fmtNum(item.fdv_to_mcap)}</div></div>
        <div class="kv"><div class="k">24h Volume</div><div class="v">${fmtMoney(item.volume_24h_usd)}</div></div>
        <div class="kv"><div class="k">24h Vol/MCAP</div><div class="v">${fmtPct(item.volume_to_mcap_pct)}</div></div>
        <div class="kv"><div class="k">7d Change</div><div class="v">${fmtPct(item.price_change_7d_pct)}</div></div>
        <div class="kv"><div class="k">30d Change</div><div class="v">${fmtPct(item.price_change_30d_pct)}</div></div>
      </div>
      <div class="list-wrap">
        <section class="list-box">
          <h4>Alpha Thesis</h4>
          <ul>${thesis}</ul>
        </section>
        <section class="list-box">
          <h4>Risk Flags</h4>
          <ul>${risks}</ul>
        </section>
      </div>
      <div class="link"><a href="${cgLink}" target="_blank" rel="noreferrer">查看 CoinGecko 页面</a></div>
    </article>
  `;
}

function pctClass(v) {
  if (v === null || v === undefined) return "";
  const n = Number(v);
  if (n > 0) return "pos";
  if (n < 0) return "neg";
  return "";
}

function makeTagTable(rows) {
  if (!rows || !rows.length) return `<article class="card">暂无已平仓标签数据</article>`;
  const body = rows
    .map(
      (r) => `
      <tr>
        <td>${r.thesis_tag || "N/A"}</td>
        <td>${r.count ?? "N/A"}</td>
        <td class="${pctClass(r.win_rate_pct)}">${fmtPct(r.win_rate_pct)}</td>
        <td class="${pctClass(r.avg_return_pct)}">${fmtSignedPct(r.avg_return_pct)}</td>
        <td class="${pctClass(r.avg_alpha_pct)}">${fmtSignedPct(r.avg_alpha_pct)}</td>
      </tr>`
    )
    .join("");
  return `
    <div class="table-shell">
      <table>
        <thead>
          <tr>
            <th>标签</th>
            <th>样本数</th>
            <th>胜率</th>
            <th>平均收益</th>
            <th>平均Alpha</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function makeTradeTable(rows) {
  if (!rows || !rows.length) return `<article class="card">暂无交易日志</article>`;
  const body = rows
    .map(
      (r) => `
      <tr>
        <td>${r.id || "N/A"}</td>
        <td>${r.symbol || "N/A"}</td>
        <td>${r.thesis_tag || "N/A"}</td>
        <td>${r.status || "N/A"}</td>
        <td>${r.benchmark_symbol || "N/A"}</td>
        <td class="${pctClass(r.return_pct)}">${fmtSignedPct(r.return_pct)}</td>
        <td class="${pctClass(r.beta_30d_pct)}">${fmtSignedPct(r.beta_30d_pct)}</td>
        <td class="${pctClass(r.alpha_pct)}">${fmtSignedPct(r.alpha_pct)}</td>
        <td class="${pctClass(r.pnl_usd)}">${fmtMoney(r.pnl_usd)}</td>
      </tr>`
    )
    .join("");
  return `
    <div class="table-shell">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>标的</th>
            <th>标签</th>
            <th>状态</th>
            <th>基准</th>
            <th>策略收益</th>
            <th>Beta(30d)</th>
            <th>Alpha</th>
            <th>PnL</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

const AUTO_REFRESH_MS = 60 * 1000;
let timer = null;

function setLastSync(lastSyncNode) {
  const now = new Date();
  const local = now.toLocaleString("zh-CN", { hour12: false });
  lastSyncNode.textContent = `页面上次同步: ${local}`;
}

async function loadData(generatedAtNode, lastSyncNode, statsNode, cardsNode, reviewStatsNode, tagTableNode, tradeTableNode) {
  const res = await fetch(`./data/watchlist.json?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data = await res.json();
  const items = Array.isArray(data.items) ? data.items : [];
  const riskCount = items.filter((x) => x.valuation_label === "RICH" || x.valuation_label === "WARN").length;
  const totalMcap = items.reduce((sum, x) => sum + (x.market_cap_usd || 0), 0);
  const avgVol = items.length
    ? items.reduce((sum, x) => sum + (x.volume_to_mcap_pct || 0), 0) / items.length
    : 0;

  generatedAtNode.textContent = `数据时间(UTC): ${data.generated_at_utc || "N/A"}`;
  statsNode.innerHTML = [
    makeStat("项目数", String(items.length)),
    makeStat("总市值", fmtMoney(totalMcap)),
    makeStat("平均24h换手(Vol/MCAP)", fmtPct(avgVol)),
    makeStat("估值预警数(WARN/RICH)", String(riskCount)),
  ].join("");

  const review = data.trade_review || {};
  const summary = review.summary || {};
  reviewStatsNode.innerHTML = [
    makeStat("总交易数", String(summary.total_trades ?? 0)),
    makeStat("已平仓", String(summary.closed_trades ?? 0)),
    makeStat("平仓胜率", fmtPct(summary.win_rate_closed_pct)),
    makeStat("平均平仓收益", fmtSignedPct(summary.avg_return_closed_pct)),
    makeStat("平均平仓Alpha", fmtSignedPct(summary.avg_alpha_closed_pct)),
    makeStat("累计PnL", fmtMoney(summary.total_pnl_usd)),
  ].join("");
  tagTableNode.innerHTML = makeTagTable(review.by_tag || []);
  tradeTableNode.innerHTML = makeTradeTable(review.trades || []);
  cardsNode.innerHTML = items.map(makeCard).join("");
  setLastSync(lastSyncNode);
}

async function init() {
  const generatedAtNode = document.getElementById("generatedAt");
  const lastSyncNode = document.getElementById("lastSyncAt");
  const statsNode = document.getElementById("stats");
  const reviewStatsNode = document.getElementById("reviewStats");
  const tagTableNode = document.getElementById("tagTable");
  const tradeTableNode = document.getElementById("tradeTable");
  const cardsNode = document.getElementById("cards");
  const refreshBtn = document.getElementById("refreshBtn");

  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    try {
      await loadData(
        generatedAtNode,
        lastSyncNode,
        statsNode,
        cardsNode,
        reviewStatsNode,
        tagTableNode,
        tradeTableNode
      );
    } catch (err) {
      generatedAtNode.textContent = "加载失败";
      cardsNode.innerHTML = `<article class="card">读取数据失败：${err.message}</article>`;
    } finally {
      refreshBtn.disabled = false;
    }
  });

  try {
    await loadData(
      generatedAtNode,
      lastSyncNode,
      statsNode,
      cardsNode,
      reviewStatsNode,
      tagTableNode,
      tradeTableNode
    );
  } catch (err) {
    generatedAtNode.textContent = "加载失败";
    lastSyncNode.textContent = "页面同步失败";
    cardsNode.innerHTML = `<article class="card">读取数据失败：${err.message}</article>`;
  }

  if (timer) clearInterval(timer);
  timer = setInterval(async () => {
    try {
      await loadData(
        generatedAtNode,
        lastSyncNode,
        statsNode,
        cardsNode,
        reviewStatsNode,
        tagTableNode,
        tradeTableNode
      );
    } catch (_) {
      // Keep current rendering and retry at next tick.
    }
  }, AUTO_REFRESH_MS);
}

init();
