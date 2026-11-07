/* 小衰同学 + TabBar 图标 + 装饰贴纸 */
(function () {
  const faces = {
    idle: `
      <circle cx="48" cy="34" r="3.2" fill="#1a1a1a"/>
      <circle cx="72" cy="34" r="3.2" fill="#1a1a1a"/>
      <path d="M52 46 Q60 52 68 46" fill="none" stroke="#1a1a1a" stroke-width="2.4" stroke-linecap="round"/>
    `,
    happy: `
      <path d="M42 34 Q48 28 54 34" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
      <path d="M66 34 Q72 28 78 34" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
      <path d="M50 46 Q60 56 70 46" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
      <circle cx="38" cy="42" r="4" fill="#ff9aa2" opacity=".85"/>
      <circle cx="82" cy="42" r="4" fill="#ff9aa2" opacity=".85"/>
    `,
    sweat: `
      <circle cx="48" cy="34" r="3.2" fill="#1a1a1a"/>
      <circle cx="72" cy="34" r="3.2" fill="#1a1a1a"/>
      <path d="M54 48 Q60 44 66 48" fill="none" stroke="#1a1a1a" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M86 22 Q90 14 94 22 Q90 28 86 22Z" fill="#7ec8e3" stroke="#1a1a1a" stroke-width="2"/>
    `,
    think: `
      <circle cx="48" cy="34" r="3.2" fill="#1a1a1a"/>
      <circle cx="72" cy="34" r="3.2" fill="#1a1a1a"/>
      <circle cx="60" cy="48" r="2.2" fill="#1a1a1a"/>
      <circle cx="92" cy="18" r="3" fill="none" stroke="#1a1a1a" stroke-width="2"/>
      <circle cx="100" cy="10" r="2" fill="none" stroke="#1a1a1a" stroke-width="1.6"/>
    `,
    cheer: `
      <path d="M42 36 Q48 30 54 36" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
      <path d="M66 36 Q72 30 78 36" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
      <path d="M48 48 Q60 62 72 48" fill="none" stroke="#1a1a1a" stroke-width="2.8" stroke-linecap="round"/>
      <path d="M24 70 L16 52" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
      <path d="M96 70 L104 52" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
    `,
  };

  function mascotSvg(mood) {
    const face = faces[mood] || faces.idle;
    return `
<svg class="mascot-svg" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <ellipse cx="60" cy="108" rx="28" ry="6" fill="#1a1a1a" opacity=".12"/>
  <path d="M28 42c0-22 16-36 32-36s32 14 32 36c0 4-1 8-2 11H30c-1-3-2-7-2-11z" fill="#6b3f24" stroke="#1a1a1a" stroke-width="2.5"/>
  <path d="M34 28c4-6 8-8 12-8M54 18c6-4 14-4 20 0M78 24c4 0 8 3 10 7" fill="none" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <ellipse cx="60" cy="48" rx="28" ry="26" fill="#ffd7b5" stroke="#1a1a1a" stroke-width="2.5"/>
  ${face}
  <path d="M28 78c8-10 20-14 32-14s24 4 32 14l6 28H22l6-28z" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M48 72v20M72 72v20" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M40 92h40" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <circle cx="54" cy="84" r="2" fill="#1a1a1a"/>
  <circle cx="66" cy="84" r="2" fill="#1a1a1a"/>
  <path d="M54 86v10M66 86v10" stroke="#1a1a1a" stroke-width="1.6"/>
</svg>`;
  }

  const tabIcons = {
    home: `
<svg class="tab-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M6 14 L16 6 L26 14 V26 H20 V18 H12 V26 H6 Z" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2" stroke-linejoin="round"/>
  <circle cx="16" cy="13" r="2" fill="#1a1a1a"/>
</svg>`,
    bank: `
<svg class="tab-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="6" y="8" width="20" height="16" rx="3" fill="#7ec8e3" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M10 13h12M10 17h12M10 21h8" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <path d="M12 8 V6 h8 v2" fill="none" stroke="#1a1a1a" stroke-width="2"/>
  <circle cx="23" cy="23" r="5" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="1.8"/>
  <path d="M21.5 23h3M23 21.5v3" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
</svg>`,
    history: `
<svg class="tab-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="7" y="5" width="18" height="22" rx="3" fill="#7ec8e3" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M11 11h10M11 16h10M11 21h6" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <circle cx="22" cy="22" r="5.5" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M22 19.5v3l2 1" fill="none" stroke="#1a1a1a" stroke-width="1.6" stroke-linecap="round"/>
</svg>`,
    me: `
<svg class="tab-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="16" cy="12" r="6" fill="#ffd7b5" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M8 27c1.5-5 5-7 8-7s6.5 2 8 7" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2" stroke-linejoin="round"/>
  <circle cx="13.5" cy="11.5" r="1.2" fill="#1a1a1a"/>
  <circle cx="18.5" cy="11.5" r="1.2" fill="#1a1a1a"/>
  <path d="M14 14.5h4" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
</svg>`,
  };

  const decos = {
    star: `
<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M24 4 L28 18 L42 18 L31 27 L35 42 L24 33 L13 42 L17 27 L6 18 L20 18 Z" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2.2" stroke-linejoin="round"/>
</svg>`,
    book: `
<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M8 10h14c3 0 5 2 5 5v23c0-2-2-3-5-3H8V10z" fill="#7ec8e3" stroke="#1a1a1a" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M40 10H26c-3 0-5 2-5 5v23c0-2 2-3 5-3h14V10z" fill="#ffb4a8" stroke="#1a1a1a" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M21 15v20" stroke="#1a1a1a" stroke-width="2"/>
</svg>`,
    flag: `
<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M12 42 V8" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M14 10h22l-5 8 5 8H14V10z" fill="#e85d4c" stroke="#1a1a1a" stroke-width="2.2" stroke-linejoin="round"/>
</svg>`,
    bulb: `
<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="24" cy="20" r="12" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2.2"/>
  <path d="M18 30h12v4c0 2-2 4-6 4s-6-2-6-4v-4z" fill="#fff" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M20 36h8M21 39h6" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <path d="M24 6v3M10 20H7M41 20h-3M13 10l-2-2M35 10l2-2" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
</svg>`,
    trophy: `
<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M14 10h20v10c0 7-5 12-10 12s-10-5-10-12V10z" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2.2"/>
  <path d="M14 14H8c0 6 3 9 6 10M34 14h6c0 6-3 9-6 10" fill="none" stroke="#1a1a1a" stroke-width="2.2"/>
  <path d="M20 32h8v4h-8zM16 38h16v4H16z" fill="#7ec8e3" stroke="#1a1a1a" stroke-width="2"/>
</svg>`,
    coin: `
<svg class="pill-icon" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="10" cy="10" r="8" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="1.8"/>
  <text x="10" y="13.5" text-anchor="middle" font-size="9" font-weight="700" fill="#1a1a1a">分</text>
</svg>`,
    exp: `
<svg class="pill-icon" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M10 2 L12.5 7.5 L18 8.2 L14 12.4 L15.2 18 L10 15 L4.8 18 L6 12.4 L2 8.2 L7.5 7.5 Z" fill="#6c8cff" stroke="#1a1a1a" stroke-width="1.6" stroke-linejoin="round"/>
</svg>`,
  };

  document.querySelectorAll("[data-mascot]").forEach((el) => {
    const mood = el.getAttribute("data-mascot") || "idle";
    const size = el.getAttribute("data-size") || "";
    el.classList.add("mascot");
    if (size) el.classList.add(size);
    el.innerHTML = mascotSvg(mood);
  });

  document.querySelectorAll("[data-deco]").forEach((el) => {
    const kind = el.getAttribute("data-deco") || "star";
    const size = el.getAttribute("data-size") || "";
    el.classList.add("deco");
    if (size) el.classList.add(size);
    el.innerHTML = decos[kind] || decos.star;
  });

  /* 货币条：data-currency="lv:5|xp:1280|coin:360" */
  document.querySelectorAll("[data-currency]").forEach((el) => {
    const raw = el.getAttribute("data-currency") || "lv:1|xp:0|coin:0";
    const map = {};
    raw.split("|").forEach((part) => {
      const [k, v] = part.split(":");
      if (k) map[k] = v;
    });
    el.classList.add("currency-bar");
    el.innerHTML = `
      <span class="pill lv">Lv.${map.lv || 1}</span>
      <span class="pill xp">${decos.exp}<span>EXP ${map.xp || 0}</span></span>
      <span class="pill coin">${decos.coin}<span>${map.coin || 0}</span></span>
    `;
  });

  document.querySelectorAll("[data-tabbar]").forEach((el) => {
    const active = el.getAttribute("data-tabbar") || "home";
    el.classList.add("tabbar");
    el.setAttribute("role", "navigation");
    el.setAttribute("aria-label", "主导航");
    el.innerHTML = [
      { id: "home", label: "开局" },
      { id: "bank", label: "题目" },
      { id: "me", label: "我的" },
    ]
      .map(
        (t) => `
      <div class="tabbar-item${t.id === active ? " active" : ""}">
        ${tabIcons[t.id]}
        <span>${t.label}</span>
      </div>`
      )
      .join("");
  });
})();
