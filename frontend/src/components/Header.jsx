import React from 'react';
import StatusIndicator from './StatusIndicator';

export default function Header({ isOnline, isChecking, onRefresh }) {
  return (
    <header className="app-header">
      <div className="header-left">
        <h1>AI Website Builder</h1>
        <p>Agents build and test it. You open the finished website.</p>
      </div>
      <div className="header-right">
        <StatusIndicator 
          isOnline={isOnline} 
          isChecking={isChecking} 
          onRefresh={onRefresh} 
        />
      </div>
    </header>
  );
}
