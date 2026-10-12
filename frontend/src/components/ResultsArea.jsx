import React, { useState, useEffect } from 'react';
import { getProjectZipDownloadUrl } from '../services/api';

export default function ResultsArea({
  requirementResult,
  planningResult,
  codeGenResult,
  testReport,
  debugReport,
  documentation,
  onRunTesting,
  onRunDebugging,
  onRunDocumentation,
  previewInfo,
  onRunPreview,
  onStopPreview,
  isWorkflowBusy,
  activeFilePath,
  activeFileContent,
  onSelectFile,
  validationResult,
  activeError,
}) {
  const [activeTab, setActiveTab] = useState('requirements');
  const [copied, setCopied] = useState(false);

  const hasReq = Boolean(requirementResult);
  const hasPlan = Boolean(planningResult);
  const hasCode = Boolean(codeGenResult && codeGenResult.manifest);
  const hasTest = Boolean(testReport);
  const hasDebug = Boolean(debugReport);
  const hasDocumentation = Boolean(documentation);
  const hasPreview = Boolean(previewInfo);
  const hasVal = Boolean(validationResult);

  // Auto-switch tabs as pipeline progresses
  useEffect(() => {
    if (hasDocumentation) {
      setActiveTab('documentation');
    } else if (hasDebug) {
      setActiveTab('debugging');
    } else if (hasPreview) {
      setActiveTab('preview');
    } else if (hasTest) {
      setActiveTab('testing');
    } else if (hasCode) {
      setActiveTab('code');
    } else if (hasPlan) {
      setActiveTab('planning');
    } else if (hasReq) {
      setActiveTab('requirements');
    }
  }, [hasPreview, hasTest, hasCode, hasPlan, hasReq, hasDebug, hasDocumentation]);

  const handleDownloadDocumentation = () => {
    if (!documentation) return;
    const blob = new Blob([documentation.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'PROJECT_GUIDE.md';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyCode = () => {
    if (!activeFileContent) return;
    navigator.clipboard.writeText(activeFileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadActiveFile = () => {
    if (!activeFileContent || !activeFilePath) return;
    const blob = new Blob([activeFileContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const filename = activeFilePath.split('/').pop() || 'file.txt';
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getFileIcon = (path) => {
    if (path.endsWith('.jsx') || path.endsWith('.js')) return '⚛️';
    if (path.endsWith('.py')) return '🐍';
    if (path.endsWith('.json')) return '📋';
    if (path.endsWith('.css')) return '🎨';
    if (path.endsWith('.html')) return '🌐';
    if (path.endsWith('.md')) return '📝';
    return '📄';
  };

  const getCheckStatusBadge = (status) => {
    switch (status) {
      case 'passed':
        return <span className="status-pill pill-passed">✓ PASSED</span>;
      case 'failed':
        return <span className="status-pill pill-failed">✕ FAILED</span>;
      case 'blocked':
        return <span className="status-pill pill-blocked">⊘ BLOCKED</span>;
      default:
        return <span className="status-pill pill-skipped">○ SKIPPED</span>;
    }
  };

  return (
    <div className="results-container">
      {/* Header & Tabs */}
      <div className="results-header">
        <div className="results-tabs">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'requirements' ? 'active' : ''}`}
            onClick={() => setActiveTab('requirements')}
            disabled={!hasReq && !hasVal}
          >
            1. Requirements {hasReq && '✓'}
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'planning' ? 'active' : ''}`}
            onClick={() => setActiveTab('planning')}
            disabled={!hasPlan}
          >
            2. Plan {hasPlan && '✓'}
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'code' ? 'active' : ''}`}
            onClick={() => setActiveTab('code')}
            disabled={!hasCode}
          >
            3. Code {hasCode && `(${codeGenResult.manifest.files_count}) ✓`}
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'testing' ? 'active' : ''}`}
            onClick={() => setActiveTab('testing')}
            disabled={!hasTest}
          >
            4. Test Report {hasTest && `(${testReport.passed_count}/${testReport.total_checks})`}
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
            disabled={!hasCode}
          >
            Website
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'debugging' ? 'active' : ''}`}
            onClick={() => setActiveTab('debugging')}
            disabled={!hasCode}
          >
            Debugging {hasDebug && '✓'}
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'documentation' ? 'active' : ''}`}
            onClick={() => setActiveTab('documentation')}
            disabled={!hasCode}
          >
            Documentation {hasDocumentation && '✓'}
          </button>
          {hasVal && !hasReq && (
            <button
              type="button"
              className={`tab-btn ${activeTab === 'validation' ? 'active' : ''}`}
              onClick={() => setActiveTab('validation')}
            >
              Validation
            </button>
          )}
        </div>
        <span className="results-mode-badge">
          {previewInfo?.status === 'running'
            ? 'WEBSITE PREVIEW READY'
            : hasTest
            ? `TESTS: ${testReport.overall_status.toUpperCase()}`
            : hasCode
            ? 'CODE GENERATED'
            : hasPlan
            ? 'PLANNING READY'
            : hasReq
            ? 'ANALYSIS READY'
            : 'STANDBY'}
        </span>
      </div>

      {/* Error Banner */}
      {activeError && (
        <div className="results-error-banner">
          <div className="error-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            Agent Error
          </div>
          <div className="error-msg">{activeError}</div>
          {activeError.includes('GEMINI_API_KEY') && (
            <div className="error-help">
              💡 <strong>How to fix:</strong> Add your Gemini API key in <code>backend/.env</code>:
              <br />
              <code>GEMINI_API_KEY=AIzaSy...</code>
              <br />
              Then click the <strong>Retry</strong> button on the failed workflow step.
            </div>
          )}
        </div>
      )}

      {/* Content Area */}
      <div className="results-body">
        {activeTab === 'preview' && hasCode && (
          <div className="agent-output-view website-preview-view">
            <div className="preview-heading">
              <div>
                <h2>Your website</h2>
                <p>
                  {previewInfo?.status === 'running'
                    ? 'The generated app is running in an isolated Docker container on this computer.'
                    : previewInfo?.status === 'stopped'
                    ? 'The preview is stopped. Start it again whenever you want to show your website.'
                    : 'The agents finished building your app. Start an isolated preview to view it.'}
                </p>
              </div>
              {previewInfo?.status === 'running' && (
                <div className="preview-actions">
                  <a
                    className="btn-open-preview"
                    href={previewInfo.preview_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open in new tab
                  </a>
                  <button type="button" className="btn-copy-code" onClick={onStopPreview}>
                    Stop preview
                  </button>
                </div>
              )}
              {previewInfo?.status !== 'running' && (
                <button
                  type="button"
                  className="btn-open-preview"
                  onClick={() => onRunPreview(codeGenResult.project_id)}
                  disabled={previewInfo?.status === 'starting' || isWorkflowBusy}
                >
                  {previewInfo?.status === 'starting' ? 'Starting website…' : 'Start website preview'}
                </button>
              )}
            </div>

            {previewInfo?.status === 'running' && (
              <>
                <div className="preview-url">
                  Website address: <a href={previewInfo.preview_url} target="_blank" rel="noreferrer">{previewInfo.preview_url}</a>
                </div>
                <iframe
                  className="preview-frame"
                  src={previewInfo.preview_url}
                  title={`${codeGenResult.manifest.project_name} live preview`}
                  sandbox="allow-forms allow-scripts allow-same-origin"
                  referrerPolicy="no-referrer"
                />
              </>
            )}

            {previewInfo?.status === 'failed' && (
              <div className="preview-error" role="alert">
                <strong>Could not start the website.</strong>
                <p>{previewInfo.error}</p>
                {previewInfo.error?.includes('Docker') && (
                  <p>
                    On Windows, install <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="noreferrer">Docker Desktop</a>,
                    open it, wait until it says it is running, then choose <strong>Start website preview</strong> again.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: TEST REPORT */}
        {activeTab === 'testing' && hasTest && (
          <div className="agent-output-view test-report-view">
            {/* Top Metrics Cards */}
            <div className="test-metrics-grid">
              <div className="test-metric-card passed">
                <div className="metric-val">{testReport.passed_count}</div>
                <div className="metric-lbl">Passed</div>
              </div>
              <div className="test-metric-card failed">
                <div className="metric-val">{testReport.failed_count}</div>
                <div className="metric-lbl">Failed</div>
              </div>
              <div className="test-metric-card blocked">
                <div className="metric-val">{testReport.blocked_count}</div>
                <div className="metric-lbl">Blocked (No Docker)</div>
              </div>
              <div className="test-metric-card total">
                <div className="metric-val">{testReport.total_checks}</div>
                <div className="metric-lbl">Total Checks</div>
              </div>
            </div>

            {/* Sandbox Isolation Notice */}
            <div className="sandbox-notice">
              <div className="sandbox-notice-title">
                🛡️ Safe Execution & Host Isolation Policy
              </div>
              <div className="sandbox-notice-text">
                Untrusted generated code was validated safely via in-process static AST parsing, syntax compilation, and structural audits.
                {testReport.blocked_count > 0 && (
                  <span>
                    {' '}Containerized runtime unit tests are reported as <strong>Blocked</strong> because Docker is not available in this environment. To protect the host machine, generated code is never executed without container isolation.
                  </span>
                )}
              </div>
            </div>

            {/* Test Checklist */}
            <div className="test-checklist">
              <div className="checklist-header">
                <h3>VERIFICATION CHECKS BREAKDOWN</h3>
                <span className="tested-at-text">Tested: {new Date(testReport.tested_at).toLocaleTimeString()}</span>
              </div>

              <div className="checklist-items">
                {testReport.checks.map((chk, i) => (
                  <div key={i} className={`check-row ${chk.status}`}>
                    <div className="check-main">
                      <div className="check-title-row">
                        <span className="check-name">{chk.name}</span>
                        <span className="check-category-tag">{chk.category}</span>
                        {chk.duration_ms > 0 && (
                          <span className="check-duration">{chk.duration_ms}ms</span>
                        )}
                      </div>
                      <div className="check-message">{chk.message}</div>
                      {chk.details && (
                        <div className="check-details-box">
                          <pre>{chk.details}</pre>
                        </div>
                      )}
                    </div>
                    <div className="check-badge-area">
                      {getCheckStatusBadge(chk.status)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'debugging' && hasCode && (
          <div className="agent-output-view">
            {!hasDebug ? (
              <div className="output-section">
                <h3>Project debugging</h3>
                <p>Analyze verification results and get targeted recommendations for failed checks.</p>
                <button type="button" className="btn-run-agent" onClick={onRunDebugging} disabled={isWorkflowBusy}>
                  Run Debugging
                </button>
              </div>
            ) : (
              <>
                <div className={`disclaimer-banner ${debugReport.status === 'clean' ? '' : 'alert-error'}`}>
                  {debugReport.summary}
                </div>
                <p className="sandbox-notice-text">
                  The debugging agent diagnoses verification failures and recommends fixes; it does not modify generated source code automatically.
                </p>
                {debugReport.findings.length === 0 ? (
                  <div className="output-section">
                    <h3>No failing checks found</h3>
                    <p>
                      {debugReport.test_report.blocked_count > 0
                        ? 'Some runtime checks were blocked by the environment. Start Docker and rerun tests for full coverage.'
                        : 'All available verification checks passed.'}
                    </p>
                  </div>
                ) : (
                  <div className="test-checklist">
                    <div className="checklist-header"><h3>DIAGNOSTIC FINDINGS</h3></div>
                    <div className="checklist-items">
                      {debugReport.findings.map((finding, index) => (
                        <div key={`${finding.check_name}-${index}`} className="check-row failed">
                          <div className="check-main">
                            <div className="check-title-row">
                              <span className="check-name">{finding.check_name}</span>
                              <span className="check-category-tag">{finding.category}</span>
                              <span className="check-category-tag">{finding.priority} priority</span>
                            </div>
                            <div className="check-message">{finding.summary}</div>
                            <div className="check-details-box"><pre>{finding.evidence}</pre></div>
                            <p><strong>Recommended action:</strong> {finding.recommended_action}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <button type="button" className="btn-retry" onClick={onRunDebugging} disabled={isWorkflowBusy}>Re-run Debugging</button>
              </>
            )}
          </div>
        )}

        {activeTab === 'documentation' && hasCode && (
          <div className="agent-output-view">
            {!hasDocumentation ? (
              <div className="output-section">
                <h3>Project documentation</h3>
                <p>Generate a project-specific setup guide and add it to the downloadable project archive.</p>
                <button type="button" className="btn-run-agent" onClick={onRunDocumentation} disabled={isWorkflowBusy}>
                  Generate Documentation
                </button>
              </div>
            ) : (
              <>
                <div className="checklist-header">
                  <h3>{documentation.file_path}</h3>
                  <button type="button" className="btn-copy-code" onClick={handleDownloadDocumentation}>
                    Download Guide
                  </button>
                </div>
                <pre className="code-lines"><code>{documentation.content}</code></pre>
              </>
            )}
          </div>
        )}

        {/* TAB 3: GENERATED CODE */}
        {activeTab === 'code' && hasCode && (
          <div className="agent-output-view code-gen-view">
            <div className="disclaimer-banner">
              ⚠️ {codeGenResult.manifest.generation_disclaimer}
            </div>

            {/* Top Toolbar */}
            <div className="code-toolbar">
              <div className="code-meta-info">
                <span className="badge-stack">{codeGenResult.manifest.target_stack}</span>
                <span className="badge-meta">{codeGenResult.manifest.files_count} files</span>
                <span className="badge-meta">{(codeGenResult.manifest.total_bytes / 1024).toFixed(1)} KB</span>
              </div>
              <div className="code-actions">
                <a
                  href={getProjectZipDownloadUrl(codeGenResult.project_id)}
                  className="btn-download-zip"
                  download
                  title="Download complete codebase as a ZIP archive"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  Download Project (ZIP)
                </a>
              </div>
            </div>

            {/* Code Workspace: Explorer + Viewer */}
            <div className="code-workspace">
              {/* File Tree Sidebar */}
              <div className="file-tree-pane">
                <div className="file-tree-header">PROJECT EXPLORER</div>
                <div className="file-tree-list">
                  {codeGenResult.manifest.file_paths.map((path) => (
                    <div
                      key={path}
                      className={`file-tree-item ${activeFilePath === path ? 'active' : ''}`}
                      onClick={() => onSelectFile(path)}
                      title={path}
                    >
                      <span className="file-tree-icon">{getFileIcon(path)}</span>
                      <span className="file-tree-name">{path}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Code Viewer Main Area */}
              <div className="code-viewer-pane">
                <div className="code-viewer-header">
                  <span className="active-path-label">
                    <code>{activeFilePath || 'Select a file to preview'}</code>
                  </span>
                  {activeFilePath && (
                    <div className="viewer-file-actions">
                      <button
                        type="button"
                        className="btn-copy-code"
                        onClick={handleCopyCode}
                        title="Copy to clipboard"
                      >
                        {copied ? '✓ Copied' : 'Copy'}
                      </button>
                      <button
                        type="button"
                        className="btn-copy-code"
                        onClick={handleDownloadActiveFile}
                        title="Download this file"
                      >
                        Download
                      </button>
                    </div>
                  )}
                </div>

                <div className="code-viewer-content">
                  {activeFileContent !== null ? (
                    <pre className="code-lines">
                      <code>{activeFileContent}</code>
                    </pre>
                  ) : (
                    <div className="empty-file-preview">
                      Select a file from the Project Explorer to preview its contents.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 1: REQUIREMENT ANALYSIS */}
        {activeTab === 'requirements' && hasReq && (
          <div className="agent-output-view">
            <div className="disclaimer-banner">
              ⚠️ {requirementResult.analysis_disclaimer}
            </div>

            <div className="output-section">
              <h3>🎯 Project Objective</h3>
              <p className="objective-text">{requirementResult.project_objective}</p>
            </div>

            <div className="output-grid-2">
              <div className="output-section">
                <h3>👤 User Requirements</h3>
                <ul className="bullet-list">
                  {requirementResult.user_requirements.map((req, i) => (
                    <li key={i}>{req}</li>
                  ))}
                </ul>
              </div>

              <div className="output-section">
                <h3>⚡ Functional Requirements</h3>
                <ul className="bullet-list">
                  {requirementResult.functional_requirements.map((fr, i) => (
                    <li key={i}>{fr}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="output-section">
              <h3>💡 Proposed Features (User vs AI Enhanced)</h3>
              <div className="feature-cards-grid">
                {requirementResult.proposed_features.map((feat, i) => (
                  <div key={i} className={`feature-item ${feat.source}`}>
                    <div className="feature-header">
                      <span className="feature-name">{feat.name}</span>
                      <span className={`feature-tag ${feat.source}`}>
                        {feat.source === 'user_specified' ? 'User Specified' : 'AI Suggested'}
                      </span>
                    </div>
                    <p className="feature-desc">{feat.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="output-grid-2">
              <div className="output-section">
                <h3>🛡️ Non-Functional Requirements</h3>
                <ul className="bullet-list">
                  {requirementResult.non_functional_requirements.map((nfr, i) => (
                    <li key={i}>{nfr}</li>
                  ))}
                </ul>
              </div>

              <div className="output-section">
                <h3>✅ Acceptance Criteria</h3>
                <ul className="bullet-list">
                  {requirementResult.acceptance_criteria.map((ac, i) => (
                    <li key={i}>{ac}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: DEVELOPMENT PLAN */}
        {activeTab === 'planning' && hasPlan && (
          <div className="agent-output-view">
            <div className="disclaimer-banner">
              ⚠️ {planningResult.planning_disclaimer}
            </div>

            <div className="output-section">
              <h3>🏛 Architecture: {planningResult.architecture.pattern}</h3>
              <p className="objective-text">{planningResult.architecture.description}</p>
            </div>

            <div className="output-grid-2">
              <div className="output-section">
                <h3>💻 Frontend Responsibilities</h3>
                <ul className="bullet-list">
                  {planningResult.architecture.frontend_responsibilities.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>

              <div className="output-section">
                <h3>⚙️ Backend Responsibilities</h3>
                <ul className="bullet-list">
                  {planningResult.architecture.backend_responsibilities.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>

            {planningResult.architecture.database_design && (
              <div className="output-section">
                <h3>🗄 Database Design</h3>
                <div className="code-box">
                  <pre>{planningResult.architecture.database_design}</pre>
                </div>
              </div>
            )}

            <div className="output-grid-2">
              <div className="output-section">
                <h3>📁 Projected File Tree</h3>
                <div className="code-box">
                  <pre>{planningResult.file_tree.join('\n')}</pre>
                </div>
              </div>

              <div className="output-section">
                <h3>📦 Planned Dependencies</h3>
                <div className="dep-list">
                  {planningResult.dependencies.map((dep, i) => (
                    <div key={i} className="dep-item">
                      <div className="dep-name">
                        <code>{dep.package_name}</code>
                        <span className={`tag-target ${dep.target}`}>{dep.target}</span>
                      </div>
                      <div className="dep-desc">{dep.purpose}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="output-section">
              <h3>🗺 Implementation Roadmap</h3>
              <div className="roadmap-steps">
                {planningResult.implementation_steps.map((step) => (
                  <div key={step.step_number} className="step-card">
                    <div className="step-badge">Step {step.step_number}</div>
                    <div className="step-details">
                      <h4>{step.title}</h4>
                      <p>{step.description}</p>
                      {step.deliverables?.length > 0 && (
                        <div className="step-deliverables">
                          Deliverables: {step.deliverables.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="output-section">
              <h3>🧪 Testing Strategy</h3>
              <ul className="bullet-list">
                {planningResult.testing_strategy.map((ts, i) => (
                  <li key={i}>{ts}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* TAB: VALIDATION ONLY */}
        {activeTab === 'validation' && hasVal && !hasReq && (
          <div className="agent-output-view">
            <div style={{ color: '#10b981', fontWeight: 600, marginBottom: 8 }}>
              ✓ Backend Input Validation Succeeded
            </div>
            <div className="code-box">
              <pre>{JSON.stringify(validationResult, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* EMPTY STATE */}
        {!hasReq && !hasPlan && !hasCode && !hasTest && !hasVal && (
          <div className="empty-state-view">
            <div className="results-empty-icon">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </svg>
            </div>
            <div className="empty-title">AI Agents Awaiting Instructions</div>
            <p className="empty-desc">
              Describe the app you want on the left and click <strong>Build My Website</strong> to start the agents.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
