import { Brand } from './Brand';

export function AuthStory() {
    return <section className="am-auth-story">
        <Brand />
        <div className="am-story-copy">
            <span className="am-eyebrow">
                Твоя следующая история
            </span>
            <h1>Любимые миры.<br />Реальные места<span>.</span></h1>
            <p>У каждого кадра есть координаты.<br />
                Скоро найдём их вместе.</p>
        </div>
        <div className="am-map-art" aria-hidden="true">
            <div className="am-map-ring am-ring-one" />
            <div className="am-map-ring am-ring-two" />
            <div className="am-map-route" />
            <span className="am-map-pin am-pin-one">✦</span>
            <span className="am-map-pin am-pin-two">✦</span>
            <span className="am-map-label">
                35°40′ N &nbsp; 139°42′ E
            </span>
            <span className="am-map-city">TOKYO, JP ↗</span>
        </div>
        <span className="am-story-footer">ANIME MEETS THE WORLD</span>
    </section>;
}
