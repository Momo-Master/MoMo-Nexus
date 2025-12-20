import { Construction } from 'lucide-react';

interface PlaceholderProps {
  title: string;
  description?: string;
}

export function Placeholder({ title, description }: PlaceholderProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
      <div className="w-20 h-20 rounded-full bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center mb-6">
        <Construction className="w-10 h-10 text-neon-cyan" />
      </div>
      <h2 className="text-2xl font-mono font-bold text-text-primary mb-2">
        {title}
      </h2>
      <p className="text-text-muted max-w-md">
        {description || 'This page is under construction. Check back soon!'}
      </p>
    </div>
  );
}

