export default function SkeletonRow({ cols = 6 }: { cols?: number }) {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 bg-gray-200 rounded" style={{ width: i === 1 ? "80%" : "60%" }} />
        </td>
      ))}
    </tr>
  );
}
