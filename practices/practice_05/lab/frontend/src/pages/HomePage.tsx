export function HomePage() {
  return <main className="home-page">
    <div className="home-grid" aria-hidden="true" />
    <div className="home-content">
      <span className="coming-soon"><i /> Карта готовится к открытию</span>
      <div className="hero-pin" aria-hidden="true">↗</div>
      <p className="eyebrow">Знакомые кадры. Новые маршруты.</p>
      <h1>AnimeMap<span>.</span></h1>
      <p className="home-description">Между вымыслом и реальностью —
        всего одна точка на карте.</p>
      <span className="placeholder-label">Скоро здесь появятся места из аниме</span>
    </div>
    <footer className="home-footer">
      <span>ТВОЙ МИР СТАНОВИТСЯ БОЛЬШЕ</span>
      <span>探索する · Исследуй</span>
    </footer>
  </main>;
}
