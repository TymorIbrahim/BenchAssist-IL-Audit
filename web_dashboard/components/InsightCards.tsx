import type { InsightCard } from "@/lib/insights";

export function InsightCards({ insights, compact }: { insights: InsightCard[]; compact?: boolean }) {
  if (!insights.length) return null;
  return (
    <div className={`insight-grid ${compact ? "insight-grid-compact" : ""}`}>
      {insights.map((card) => (
        <article key={card.id} className={`insight-card ${card.requiresReview ? "insight-review" : ""}`}>
          <p>{card.text}</p>
          {card.caution ? <p className="insight-caution">{card.caution}</p> : null}
          {card.requiresReview ? <span className="insight-tag">Requires review</span> : null}
        </article>
      ))}
    </div>
  );
}
