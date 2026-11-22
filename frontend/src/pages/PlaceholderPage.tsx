type Props = {
  title: string;
  description: string;
};

export default function PlaceholderPage({ title, description }: Props) {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold m-0">{title}</h1>
      <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
        {description}
      </p>
      <div
        className="rounded-xl border p-5 text-sm"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        This page is wired into navigation and will be filled with live API data as Phases 5–8 land.
        Buttons that are not yet implemented will not claim fake success.
      </div>
    </div>
  );
}
