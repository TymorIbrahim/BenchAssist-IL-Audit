import { GLOSSARY } from "@/lib/types";
import { Card } from "./Card";

export function Glossary() {
  return (
    <Card title="Plain-language glossary">
      <dl className="glossary">
        {GLOSSARY.map((item) => (
          <div key={item.term} className="glossary-item">
            <dt>{item.term}</dt>
            <dd>{item.definition}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
