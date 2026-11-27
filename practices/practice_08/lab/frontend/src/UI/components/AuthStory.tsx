import { Brand } from './Brand';

export function AuthStory() {
  return <section className="auth-story">
      <Brand />
      <div className="story-copy">
        <span className="eyebrow">Твоя следующая история</span>
        <h1>Любимые миры.<br />Реальные места<span>.</span></h1>
        <p>У каждого кадра есть координаты.<br />
          Скоро найдём их вместе.</p>
      </div>
      <div className="map-art" aria-hidden="true">
        <div className="map-ring ring-one" />
        <div className="map-ring ring-two" />
        <div className="map-route" />
        <span className="map-pin pin-one">✦</span>
        <span className="map-pin pin-two">✦</span>
        <span className="map-label">35°40′ N &nbsp; 139°42′ E</span>
        <span className="map-city">TOKYO, JP ↗</span>
      </div>
      <span className="story-footer">ANIME MEETS THE WORLD</span>
    </section>;
}
