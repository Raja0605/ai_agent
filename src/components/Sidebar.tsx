import React from 'react';
import { Briefcase, FileText, BarChart3, History, X, Zap, Cpu } from 'lucide-react';
import type { Tab } from './Header';

interface SidebarProps {
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
  isOpen: boolean;
  onToggle: () => void;
  appliedCount: number;
  aiConfig: { configured: boolean; providerName?: string } | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isOpen,
  onToggle,
  appliedCount,
  aiConfig,
}) => {
  const menuItems = [
    { id: 'jobs' as Tab, icon: Briefcase, label: 'Jobs' },
    { id: 'tracker' as Tab, icon: History, label: 'Applications', badge: appliedCount || undefined },
    { id: 'loops' as Tab, icon: Zap, label: 'Saved Searches' },
    { id: 'analytics' as Tab, icon: BarChart3, label: 'Analytics' },
    { id: 'resumes' as Tab, icon: FileText, label: 'Resumes' },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 bg-white border-r border-gray-200 w-64 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Briefcase className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-gray-900 text-lg">JobPulse</span>
            </div>
            <button
              onClick={onToggle}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>

          {/* AI Status */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 border border-gray-200">
              <Cpu className={`w-4 h-4 ${aiConfig?.configured ? 'text-blue-600' : 'text-gray-400'}`} />
              <span className="text-xs font-medium text-gray-700">
                {aiConfig?.configured ? `AI: ${aiConfig.providerName}` : 'Keyword matching'}
              </span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {menuItems.map(item => (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  if (window.innerWidth < 1024) onToggle();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-all ${
                  activeTab === item.id
                    ? 'bg-blue-50 text-blue-700 font-semibold'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center gap-3">
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="px-2 py-0.5 text-xs font-semibold bg-blue-600 text-white rounded-full">
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              Job aggregation & tracking
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};
