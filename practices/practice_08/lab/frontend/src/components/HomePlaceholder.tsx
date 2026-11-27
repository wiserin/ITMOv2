export function HomePlaceholder() {
    return <main className="am-home-page">
        <div className="am-home-grid" aria-hidden="true" />
        <div className="am-home-content">
            <span className="am-coming-soon">
                <i /> Карта готовится к открытию
            </span>
            <div className="am-hero-pin" aria-hidden="true">↗</div>
            <p className="am-eyebrow">Знакомые кадры. Новые маршруты.</p>
            <h1>AnimeMap<span>.</span></h1>
            <p className="am-home-description">Между вымыслом и реальностью —
                всего одна точка на карте.</p>
            <span className="am-placeholder-label">
                Скоро здесь появятся места из аниме
            </span>
        </div>
        <footer className="am-home-footer">
            <span>ТВОЙ МИР СТАНОВИТСЯ БОЛЬШЕ</span>
            <span>探索する · Исследуй</span>
        </footer>
    </main>;
}
