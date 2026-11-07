export const SANGIHE_LANDING_HTML = `<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sangihe.org — Portal Digital & Ekosistem AI Bahasa Sangihe</title>
  <meta name="description" content="Portal utama Sangihe.org sedang dalam pengembangan. Jelajahi layanan aktif kami: Sangiang Translate (Mesin Penerjemah Bahasa Sangihe) dan Sangiang Chat (Sahabat Diskusi AI Sangihe).">
  <link rel="icon" type="image/jpeg" href="/static/sangiang.jpeg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-deep-purple: #120224;
      --bg-royal-purple: #1f063b;
      --bg-card-purple: rgba(38, 10, 71, 0.78);
      --border-purple: rgba(181, 84, 255, 0.32);
      --border-gold: rgba(255, 213, 107, 0.45);
      --gold-bright: #ffe28a;
      --gold-primary: #f5b942;
      --gold-amber: #d97706;
      --violet-glow: #b554ff;
      --text-cream: #fdf8ee;
      --text-muted: #d6c5eb;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      min-height: 100vh;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-deep-purple);
      background-image:
        radial-gradient(circle at 50% 12%, rgba(245, 185, 66, 0.16) 0%, transparent 48%),
        radial-gradient(circle at 15% 35%, rgba(181, 84, 255, 0.22) 0%, transparent 50%),
        radial-gradient(circle at 85% 75%, rgba(147, 51, 234, 0.24) 0%, transparent 52%),
        linear-gradient(180deg, #1b0435 0%, #120224 55%, #0d011a 100%);
      color: var(--text-cream);
      display: flex;
      flex-direction: column;
      align-items: center;
      overflow-x: hidden;
      position: relative;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(255, 213, 107, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(181, 84, 255, 0.04) 1px, transparent 1px);
      background-size: 44px 44px;
      pointer-events: none;
      z-index: 0;
    }

    .top-bar {
      width: 100%;
      max-width: 1120px;
      padding: 1.5rem 1.5rem 0.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 2;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .brand-identity {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      text-decoration: none;
    }

    .brand-logo {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      object-fit: cover;
      border: 2px solid var(--gold-primary);
      box-shadow: 0 0 18px rgba(245, 185, 66, 0.45);
    }

    .brand-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.35rem;
      font-weight: 800;
      letter-spacing: 0.03em;
      background: linear-gradient(135deg, #fff6d6 0%, #ffd56b 50%, #f59e0b 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-subtitle {
      font-size: 0.76rem;
      color: var(--text-muted);
      letter-spacing: 0.04em;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.42rem 0.95rem;
      border-radius: 999px;
      background: rgba(245, 185, 66, 0.12);
      border: 1px solid rgba(255, 213, 107, 0.4);
      color: var(--gold-bright);
      font-size: 0.8rem;
      font-weight: 600;
      box-shadow: 0 0 20px rgba(245, 185, 66, 0.15);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--gold-bright);
      box-shadow: 0 0 10px var(--gold-bright);
      animation: pulseGold 2s infinite ease-in-out;
    }

    @keyframes pulseGold {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.3); opacity: 0.65; }
    }

    .main-container {
      width: 100%;
      max-width: 1060px;
      padding: 1rem 1.5rem 3.5rem;
      z-index: 2;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .hero-artwork-wrap {
      width: 100%;
      max-width: 920px;
      margin: 0.5rem auto 2rem;
      border-radius: 22px;
      padding: 4px;
      background: linear-gradient(135deg, rgba(255, 213, 107, 0.75) 0%, rgba(181, 84, 255, 0.65) 50%, rgba(245, 158, 11, 0.75) 100%);
      box-shadow:
        0 20px 55px rgba(10, 1, 22, 0.85),
        0 0 42px rgba(181, 84, 255, 0.28),
        0 0 28px rgba(245, 185, 66, 0.22);
      overflow: hidden;
      position: relative;
    }

    .hero-artwork-inner {
      border-radius: 19px;
      overflow: hidden;
      background: #190430;
      display: flex;
    }

    .hero-artwork-img {
      width: 100%;
      height: auto;
      display: block;
      object-fit: cover;
    }

    .greeting-badge {
      display: inline-block;
      font-family: 'Outfit', sans-serif;
      font-size: 0.9rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--gold-bright);
      margin-bottom: 0.65rem;
    }

    .hero-heading {
      font-family: 'Outfit', sans-serif;
      font-size: clamp(1.75rem, 4vw, 2.65rem);
      font-weight: 800;
      line-height: 1.22;
      margin-bottom: 0.95rem;
      background: linear-gradient(135deg, #ffffff 0%, #ffe699 55%, #f5b942 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 4px 24px rgba(245, 185, 66, 0.18);
    }

    .hero-description {
      max-width: 740px;
      font-size: clamp(0.98rem, 2vw, 1.12rem);
      line-height: 1.7;
      color: var(--text-muted);
      margin-bottom: 2.25rem;
    }

    .hero-description strong {
      color: var(--gold-bright);
      font-weight: 600;
    }

    .services-grid {
      width: 100%;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.5rem;
      margin-top: 0.25rem;
    }

    .service-card {
      position: relative;
      background: linear-gradient(160deg, rgba(49, 12, 92, 0.85) 0%, rgba(25, 5, 48, 0.92) 100%);
      border: 1px solid var(--border-gold);
      border-radius: 20px;
      padding: 2rem 1.85rem;
      text-align: left;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow:
        0 14px 36px rgba(9, 1, 20, 0.7),
        inset 0 1px 0 rgba(255, 226, 138, 0.25);
      transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
      text-decoration: none;
      color: inherit;
      overflow: hidden;
    }

    .service-card::before {
      content: "";
      position: absolute;
      top: -50%;
      right: -30%;
      width: 240px;
      height: 240px;
      background: radial-gradient(circle, rgba(245, 185, 66, 0.16) 0%, transparent 70%);
      pointer-events: none;
    }

    .service-card:hover {
      transform: translateY(-5px);
      border-color: var(--gold-bright);
      box-shadow:
        0 20px 44px rgba(10, 1, 24, 0.85),
        0 0 30px rgba(245, 185, 66, 0.28),
        0 0 20px rgba(181, 84, 255, 0.25);
    }

    .card-top-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.15rem;
    }

    .service-icon-box {
      width: 52px;
      height: 52px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, rgba(245, 185, 66, 0.22) 0%, rgba(181, 84, 255, 0.28) 100%);
      border: 1px solid rgba(255, 213, 107, 0.5);
      color: var(--gold-bright);
      box-shadow: 0 0 18px rgba(245, 185, 66, 0.2);
    }

    .service-tag {
      font-size: 0.74rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0.3rem 0.75rem;
      border-radius: 999px;
      background: rgba(245, 185, 66, 0.16);
      border: 1px solid rgba(255, 213, 107, 0.4);
      color: var(--gold-bright);
    }

    .service-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.45rem;
      font-weight: 700;
      color: #fff8e6;
      margin-bottom: 0.55rem;
    }

    .service-desc {
      font-size: 0.94rem;
      line-height: 1.62;
      color: var(--text-muted);
      margin-bottom: 1.65rem;
    }

    .service-cta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.55rem;
      width: 100%;
      padding: 0.88rem 1.25rem;
      border-radius: 12px;
      font-family: 'Outfit', sans-serif;
      font-size: 0.98rem;
      font-weight: 700;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .service-cta-gold {
      background: linear-gradient(135deg, #ffd56b 0%, #f59e0b 100%);
      color: #1a0430;
      box-shadow: 0 6px 20px rgba(245, 158, 11, 0.38);
    }

    .service-card:hover .service-cta-gold {
      background: linear-gradient(135deg, #ffe494 0%, #fbbf24 100%);
      box-shadow: 0 8px 26px rgba(245, 185, 66, 0.55);
    }

    .service-cta-purple-gold {
      background: linear-gradient(135deg, #7e22ce 0%, #581c87 100%);
      color: var(--gold-bright);
      border: 1px solid var(--gold-primary);
      box-shadow: 0 6px 20px rgba(126, 34, 206, 0.45);
    }

    .service-card:hover .service-cta-purple-gold {
      background: linear-gradient(135deg, #9333ea 0%, #6b21a8 100%);
      box-shadow: 0 8px 26px rgba(168, 85, 247, 0.6);
    }

    .landing-footer {
      width: 100%;
      padding: 1.5rem;
      border-top: 1px solid rgba(255, 213, 107, 0.16);
      background: rgba(13, 1, 26, 0.75);
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
      z-index: 2;
      margin-top: auto;
    }

    .landing-footer strong {
      color: var(--gold-bright);
      font-weight: 600;
    }

    @media (max-width: 768px) {
      .top-bar {
        justify-content: center;
        text-align: center;
      }
      .services-grid {
        grid-template-columns: 1fr;
      }
      .service-card {
        padding: 1.5rem 1.35rem;
      }
    }
  </style>
</head>
<body>

  <header class="top-bar">
    <a href="https://sangihe.org" class="brand-identity">
      <img src="/static/sangiang.jpeg" alt="Sangiang" class="brand-logo">
      <div style="text-align: left;">
        <div class="brand-title">SANGIHE.ORG</div>
        <div class="brand-subtitle">Ekosistem Digital &amp; Kecerdasan Buatan Sangihe</div>
      </div>
    </a>
    <div class="status-pill">
      <span class="status-dot"></span>
      <span>Situs Induk Sedang Dalam Pembangunan</span>
    </div>
  </header>

  <main class="main-container">
    <div class="hero-artwork-wrap">
      <div class="hero-artwork-inner">
        <img
          src="/static/sangihe_org_underconstruction.jpeg"
          alt="Sangihe.org Under Construction — We Are Building Something Amazing"
          class="hero-artwork-img"
        >
      </div>
    </div>

    <span class="greeting-badge">✦ Tabea Kawanua &amp; Sahabat Nusantara ✦</span>
    <h1 class="hero-heading">Kami Sedang Membangun Sesuatu yang Istimewa untuk Sangihe</h1>
    <p class="hero-description">
      Portal utama <strong>sangihe.org</strong> saat ini sedang dalam tahap pembangunan dan pemeliharaan.
      Selagi kami menyiapkan wajah baru portal ini, Anda sudah dapat mencoba langsung layanan kecerdasan buatan
      <strong>Sangiang Translate</strong> dan <strong>Sangiang Chat</strong> di bawah ini:
    </p>

    <div class="services-grid">
      <a href="https://translate.sangihe.org" id="link-translate" class="service-card">
        <div>
          <div class="card-top-row">
            <div class="service-icon-box">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m5 8 6 6"></path>
                <path d="m4 14 6-6 2-3"></path>
                <path d="M2 5h12"></path>
                <path d="M7 2h1"></path>
                <path d="m22 22-5-10-5 10"></path>
                <path d="M14 18h6"></path>
              </svg>
            </div>
            <span class="service-tag" id="tag-translate">Aktif • translate.sangihe.org</span>
          </div>
          <h2 class="service-title">Sangiang Translate</h2>
          <p class="service-desc">
            Mesin penerjemah dua arah <strong>Bahasa Sangihe ⇄ Bahasa Indonesia</strong>. Dilengkapi fitur pemulihan tanda diakritik Sangihe otomatis, pencarian kamus, serta analisis morfologi kata.
          </p>
        </div>
        <div class="service-cta service-cta-gold">
          <span>Coba Sangiang Translate</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </div>
      </a>

      <a href="https://chat.sangihe.org" id="link-chat" class="service-card">
        <div>
          <div class="card-top-row">
            <div class="service-icon-box">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                <path d="M8 10h.01"></path>
                <path d="M12 10h.01"></path>
                <path d="M16 10h.01"></path>
              </svg>
            </div>
            <span class="service-tag" id="tag-chat">Aktif • chat.sangihe.org</span>
          </div>
          <h2 class="service-title">Sangiang Chat</h2>
          <p class="service-desc">
            Sahabat diskusi AI cerdas untuk mengobrol dan belajar percakapan <strong>Bahasa Sangihe</strong> sehari-hari, budaya bahari, sejarah, serta kearifan lokal Kepulauan Sangihe.
          </p>
        </div>
        <div class="service-cta service-cta-purple-gold">
          <span>Mulai Mengobrol di Sangiang Chat</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </div>
      </a>
    </div>
  </main>

  <footer class="landing-footer">
    <p>
      <strong>Sangihe.org</strong> • Inisiator Proyek: <strong>Yayasan Cipta Manggala Dwipa</strong> • Rekayasa Sistem AI &amp; Penerjemah: <strong>Divisi DigiLab CMD</strong>
    </p>
  </footer>

  <script>
    if (window.location.hostname === "dev.sangihe.org") {
      const lt = document.getElementById("link-translate");
      const tt = document.getElementById("tag-translate");
      const lc = document.getElementById("link-chat");
      const tc = document.getElementById("tag-chat");
      if (lt) lt.href = "https://dev-translate.sangihe.org";
      if (tt) tt.textContent = "Dev • dev-translate.sangihe.org";
      if (lc) lc.href = "https://dev-chat.sangihe.org";
      if (tc) tc.textContent = "Dev • dev-chat.sangihe.org";
    }
  </script>
</body>
</html>`;

