import { Search } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({
  title = "No results found",
  description = "Try adjusting your search or filter criteria.",
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
        {icon ?? <Search className="w-7 h-7 text-white/20" />}
      </div>
      <h3 className="text-lg font-semibold text-white/60 mb-1">{title}</h3>
      <p className="text-sm text-white/30 max-w-xs">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 rounded-lg bg-amber-400/10 text-amber-400 border border-amber-400/20 text-sm hover:bg-amber-400/20 transition-all"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
