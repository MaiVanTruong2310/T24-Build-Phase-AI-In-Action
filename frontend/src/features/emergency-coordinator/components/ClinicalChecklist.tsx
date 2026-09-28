import React, { memo } from 'react';

export type Task = {
  id: string;
  title: string;
  desc: string;
};

type Props = {
  tasks: Task[];
  checked: Record<string, boolean>;
  onToggle: (id: string) => void;
};

export const ClinicalChecklist = memo(({ tasks, checked, onToggle }: Props) => (
  <div className="grid grid-cols-2 gap-3 mb-4">
    {tasks.map(t => (
      <label key={t.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 border border-transparent hover:border-gray-200 transition-colors">
        <input 
          type="checkbox" 
          className="mt-1 w-5 h-5 text-teal-600 rounded focus:ring-teal-500"
          checked={!!checked[t.id]}
          onChange={() => onToggle(t.id)}
        />
        <div>
          <div className="font-semibold text-gray-900">{t.title}</div>
          <div className="text-sm text-gray-500">{t.desc}</div>
        </div>
      </label>
    ))}
  </div>
));
