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

async function init() {
  const generatedAtNode = document.getElementById("generatedAt");
  const statsNode = document.getElementById("stats");
  const cardsNode = document.getElementById("cards");
  document.getElementById("refreshBtn").addEventListener("click", () => window.location.reload());

  try {
    const res = await fetch("./data/watchlist.json", { cache: "no-store" });
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
    cardsNode.innerHTML = items.map(makeCard).join("");
  } catch (err) {
    generatedAtNode.textContent = "加载失败";
    cardsNode.innerHTML = `<article class="card">读取数据失败：${err.message}</article>`;
  }
}

init();

