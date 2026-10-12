import React from 'react';

export default function StatusIndicator({ isOnline, isChecking, onRefresh }) {
  let statusClass = 'checking';
  let statusText = 'Checking connection...';

  if (!isChecking) {
    if (isOnline) {
      statusClass = 'online';
      statusText = 'Backend Online (Port 8000)';
    } else {
      statusClass = 'offline';
      statusText = 'Backend Offline';
    }
  }

  return (
    <button
      type="button"
      className={`status-indicator-badge ${statusClass}`}
      title="Click to recheck backend connectivity"
      onClick={onRefresh}
      role="status"
      aria-label={`${statusText}. Activate to check again.`}
      disabled={isChecking}
    >
      <span className="status-dot"></span>
      <span>{statusText}</span>
    </button>
  );
}
