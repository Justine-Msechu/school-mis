import { Construction } from "lucide-react";

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 p-8 text-center">
      <Construction size={32} className="text-gray-300 mb-3" />
      <h2 className="text-base font-semibold text-gray-700">{title}</h2>
      <p className="text-sm text-gray-400 mt-1">This module is being migrated to the new interface.</p>
    </div>
  );
}
