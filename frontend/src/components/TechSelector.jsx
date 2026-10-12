import React from 'react';

const AVAILABLE_TECH = [
  { id: 'React', name: 'React', desc: 'Frontend UI library', required: true },
  { id: 'Python', name: 'Python', desc: 'FastAPI backend' },
  { id: 'Node.js', name: 'Node.js', desc: 'Express backend' },
  { id: 'SQLite', name: 'SQLite', desc: 'Embedded SQL database', required: true },
];

export default function TechSelector({ selectedTechnologies, onChange, disabled = false }) {
  const selectTechnology = (techId) => {
    if (disabled || techId === 'React' || techId === 'SQLite') return;
    if (selectedTechnologies.includes(techId)) return;

    onChange([
      ...selectedTechnologies.filter((technology) => technology !== 'Python' && technology !== 'Node.js'),
      techId,
    ]);
  };

  return (
    <div className="form-group">
      <label className="form-label">
        Technology Stack <span className="req">*</span>
      </label>
      <div className="tech-grid" role="group" aria-label="Supported technology stack">
        {AVAILABLE_TECH.map((tech) => {
          const isSelected = selectedTechnologies.includes(tech.id);
          const isBackend = tech.id === 'Python' || tech.id === 'Node.js';
          return (
            <div
              key={tech.id}
              className={`tech-chip ${isSelected ? 'selected' : ''} ${tech.required ? 'required' : ''}`}
              onClick={() => selectTechnology(tech.id)}
              role={isBackend ? 'radio' : 'checkbox'}
              aria-checked={isSelected}
              aria-disabled={disabled || tech.required}
              tabIndex={disabled || tech.required ? -1 : 0}
              onKeyDown={(event) => {
                if (event.key === ' ' || event.key === 'Enter') {
                  event.preventDefault();
                  selectTechnology(tech.id);
                }
              }}
            >
              <div className="tech-info">
                <div>
                  <div className="tech-name">{tech.name}</div>
                  <div className="form-hint" style={{ marginTop: 2 }}>{tech.desc}</div>
                </div>
              </div>
              <div className="tech-checkbox">{isSelected ? '✓' : ''}</div>
            </div>
          );
        })}
      </div>
      <div className="form-hint">
        React and SQLite are included. Choose either Python/FastAPI or Node.js/Express.
      </div>
    </div>
  );
}
