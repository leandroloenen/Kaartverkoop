(function () {
  var script = document.currentScript;
  var GA = script && script.getAttribute("data-ga");
  var PRIVACY = (script && script.getAttribute("data-privacy")) || "privacy/";
  if (!GA) return;
  var EN = (script && script.getAttribute("data-lang")) === "en";
  var T = EN ? {
    label: "Cookie settings",
    tekst: "May we keep anonymous visitor statistics with Google Analytics? Google places cookies for this. Without your consent we do not measure anything. Read more in the ",
    link: "privacy policy", ja: "Accept", nee: "Decline"
  } : {
    label: "Cookie-instellingen",
    tekst: "Mogen wij anonieme bezoekersstatistieken bijhouden met Google Analytics? Daarvoor plaatst Google cookies. Zonder toestemming meten wij niets. Lees meer in de ",
    link: "privacyverklaring", ja: "Accepteren", nee: "Weigeren"
  };
  var SLEUTEL = "cookie_toestemming";

  function lees() { try { return localStorage.getItem(SLEUTEL); } catch (e) { return null; } }
  function bewaar(w) { try { localStorage.setItem(SLEUTEL, w); } catch (e) {} }

  function laad() {
    if (window.__gaGeladen) return;
    window.__gaGeladen = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", GA, { allow_google_signals: false, allow_ad_personalization_signals: false });
  }

  function verwijderCookies() {
    var namen = document.cookie.split(";").map(function (c) { return c.split("=")[0].trim(); })
      .filter(function (n) { return n === "_ga" || n.indexOf("_ga_") === 0 || n === "_gid" || n.indexOf("_gat") === 0; });
    var delen = location.hostname.split(".");
    var domeinen = ["", location.hostname, "." + location.hostname];
    if (delen.length > 2) domeinen.push("." + delen.slice(-2).join("."));
    else domeinen.push("." + location.hostname.replace(/^www\./, ""));
    namen.forEach(function (n) {
      domeinen.forEach(function (d) {
        document.cookie = n + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + (d ? "; domain=" + d : "");
      });
    });
  }

  function toonBanner() {
    var oud = document.getElementById("cookiebanner");
    if (oud) oud.remove();
    var stijl = document.createElement("style");
    stijl.textContent =
      "#cookiebanner{position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#fffdf8;color:#14213d;border-top:2px solid #e8a500;" +
      "padding:14px 16px calc(14px + env(safe-area-inset-bottom,0px));font:15px/1.45 system-ui,sans-serif;box-shadow:0 -4px 20px rgba(0,0,0,.15)}" +
      "#cookiebanner .in{max-width:820px;margin:0 auto}#cookiebanner p{margin:0 0 10px}#cookiebanner a{color:inherit}" +
      "#cookiebanner button{font:inherit;font-weight:600;padding:9px 18px;margin-right:10px;border-radius:8px;border:2px solid #14213d;background:#fffdf8;color:#14213d;cursor:pointer}" +
      "@media (prefers-color-scheme:dark){#cookiebanner{background:#18203a;color:#eef0f7;border-top-color:#f2b705}#cookiebanner button{background:#18203a;color:#eef0f7;border-color:#eef0f7}}";
    var b = document.createElement("div");
    b.id = "cookiebanner";
    b.setAttribute("role", "dialog");
    b.setAttribute("aria-label", T.label);
    b.innerHTML = '<div class="in"><p>' + T.tekst + '<a href="' + PRIVACY + '">' + T.link + '</a>.</p>' +
      '<button type="button" id="cb-ja">' + T.ja + '</button><button type="button" id="cb-nee">' + T.nee + '</button></div>';
    document.head.appendChild(stijl);
    document.body.appendChild(b);
    document.getElementById("cb-ja").onclick = function () { bewaar("ja"); b.remove(); laad(); };
    document.getElementById("cb-nee").onclick = function () { bewaar("nee"); verwijderCookies(); b.remove(); };
  }

  window.cookieInstellingen = toonBanner;
  function start() {
    // Eigen bezoek uitsluiten: open eenmalig ?geen_meting=1 op je eigen apparaat (en ?geen_meting=0 om het te herstellen).
    var m = /[?&]geen_meting=(\d)/.exec(location.search);
    try {
      if (m) { if (m[1] === "1") localStorage.setItem("geen_meting", "1"); else localStorage.removeItem("geen_meting"); }
      if (localStorage.getItem("geen_meting") === "1") return;
    } catch (e) {}
    var k = lees();
    if (k === "ja") laad(); else if (k === null) toonBanner();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
