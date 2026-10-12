import React from 'react';

const WORKFLOW_STEPS = [
  { id: 'req', name: 'Requirement Analysis', desc: 'Extracts user requirements, AI suggestions & acceptance criteria' },
  { id: 'plan', name: 'Planning', desc: 'Synthesizes architecture, file tree, dependencies & roadmap' },
  { id: 'code', name: 'Code Generation', desc: 'Generates full-stack codebase with frontend, backend & SQLite' },
  { id: 'test', name: 'Testing', desc: 'Executes structural, AST syntax, dependency & container tests' },
  { id: 'preview', name: 'Website Preview', desc: 'Starts the finished website in an isolated Docker container' },
  { id: 'debug', name: 'Debugging', desc: 'Analyzes failed checks and recommends targeted fixes' },
  { id: 'doc', name: 'Documentation', desc: 'Generates a setup guide and adds it to the project archive' },
];

export default function WorkflowPanel({
  workflowStatus,
  onRunRequirementAnalysis,
  onRunPlanning,
  onRunCodeGeneration,
  onRunTesting,
  onRunPreview,
  onStopPreview,
  onRunDebugging,
  onRunDocumentation,
  previewInfo,
  isWorkflowBusy,
  hasRequirementResult,
  hasPlanningResult,
  hasCodeGenResult,
}) {
  const getBadgeClass = (status) => {
    switch (status) {
      case 'Completed':
        return 'badge-completed';
      case 'Analyzing...':
      case 'Planning...':
      case 'Generating Code...':
      case 'Running Tests...':
      case 'Starting Preview...':
      case 'Running Debugging...':
      case 'Generating Documentation...':
      case 'In progress':
        return 'badge-running';
      case 'Failed':
        return 'badge-failed';
      case 'Blocked':
        return 'badge-blocked';
      default:
        return 'badge-not-started';
    }
  };

  const isReqRunning = workflowStatus['Requirement Analysis'] === 'Analyzing...';
  const isPlanRunning = workflowStatus['Planning'] === 'Planning...';
  const isCodeRunning = workflowStatus['Code Generation'] === 'Generating Code...';
  const isTestRunning = workflowStatus['Testing'] === 'Running Tests...';

  return (
    <div className="workflow-section">
      <div className="workflow-stack">
        {WORKFLOW_STEPS.map((step, index) => {
          const status = workflowStatus[step.name] || 'Not started';
          const isReqStep = step.name === 'Requirement Analysis';
          const isPlanStep = step.name === 'Planning';
          const isCodeStep = step.name === 'Code Generation';
          const isTestStep = step.name === 'Testing';
          const isPreviewStep = step.name === 'Website Preview';
          const isDebugStep = step.name === 'Debugging';
          const isDocumentationStep = step.name === 'Documentation';

          return (
            <div key={step.id} className={`workflow-card ${status === 'Completed' ? 'card-completed' : ''}`}>
              <div className="workflow-info">
                <div className={`workflow-num ${status === 'Completed' ? 'num-completed' : ''}`}>
                  {status === 'Completed' ? '✓' : index + 1}
                </div>
                <div>
                  <div className="workflow-title">{step.name}</div>
                  <div className="card-subtitle">{step.desc}</div>
                </div>
              </div>

              <div className="workflow-actions">
                <span className={`badge-status ${getBadgeClass(status)}`}>
                  {status}
                </span>

                {/* Agent 1 Controls */}
                {isReqStep && status === 'Failed' && (
                  <button
                    type="button"
                    className="btn-retry"
                    onClick={onRunRequirementAnalysis}
                    disabled={isReqRunning}
                    title="Retry Requirement Analysis"
                  >
                    Retry
                  </button>
                )}

                {/* Agent 2 Controls */}
                {isPlanStep && (status === 'Not started' || status === 'Failed') && hasRequirementResult && (
                  <button
                    type="button"
                    className="btn-run-agent"
                    onClick={onRunPlanning}
                    disabled={isPlanRunning || isReqRunning}
                    title="Trigger Development Planning Agent"
                  >
                    {status === 'Failed' ? 'Retry Plan' : 'Run Planning'}
                  </button>
                )}

                {isPlanStep && status === 'Completed' && (
                  <button
                    type="button"
                    className="btn-retry"
                    onClick={onRunPlanning}
                    disabled={isPlanRunning || isCodeRunning || isTestRunning}
                    title="Re-run Development Planning"
                  >
                    Re-run
                  </button>
                )}

                {/* Agent 3: Code Generation Controls */}
                {isCodeStep && (status === 'Not started' || status === 'Failed') && hasPlanningResult && (
                  <button
                    type="button"
                    className="btn-run-agent btn-code-gen"
                    onClick={onRunCodeGeneration}
                    disabled={isCodeRunning || isPlanRunning || isReqRunning}
                    title="Trigger Code Generation Agent"
                  >
                    {status === 'Failed' ? 'Retry Generation' : 'Generate Code'}
                  </button>
                )}

                {isCodeStep && status === 'Completed' && (
                  <button
                    type="button"
                    className="btn-retry"
                    onClick={onRunCodeGeneration}
                    disabled={isCodeRunning || isTestRunning}
                    title="Re-run Code Generation"
                  >
                    Re-generate
                  </button>
                )}

                {/* Agent 4: Testing Agent Controls */}
                {isTestStep && (status === 'Not started' || status === 'Failed' || status === 'Blocked') && hasCodeGenResult && (
                  <button
                    type="button"
                    className="btn-run-agent btn-test-agent"
                    onClick={onRunTesting}
                    disabled={isTestRunning || isCodeRunning}
                    title="Run Verification Tests"
                  >
                    {status === 'Failed' || status === 'Blocked' ? 'Retry Tests' : 'Run Tests'}
                  </button>
                )}

                {isTestStep && status === 'Completed' && (
                  <button
                    type="button"
                    className="btn-retry"
                    onClick={onRunTesting}
                    disabled={isTestRunning}
                    title="Re-run Verification Tests"
                  >
                    Re-run
                  </button>
                )}

                {isPreviewStep && hasCodeGenResult && previewInfo?.status !== 'running' && (
                  <button
                    type="button"
                    className="btn-run-agent"
                    onClick={() => onRunPreview()}
                    disabled={isWorkflowBusy}
                    title="Start the generated website in an isolated Docker preview"
                  >
                    {status === 'Starting Preview...' ? 'Starting...' : 'Preview Website'}
                  </button>
                )}

                {isPreviewStep && previewInfo?.status === 'running' && (
                  <button type="button" className="btn-retry" onClick={onStopPreview}>
                    Stop Preview
                  </button>
                )}

                {isDebugStep && hasCodeGenResult && status !== 'Completed' && (
                  <button
                    type="button"
                    className="btn-run-agent"
                    onClick={onRunDebugging}
                    disabled={isWorkflowBusy}
                  >
                    {status === 'Failed' ? 'Retry Debugging' : 'Run Debugging'}
                  </button>
                )}

                {isDebugStep && status === 'Completed' && (
                  <button type="button" className="btn-retry" onClick={onRunDebugging}>
                    Re-run
                  </button>
                )}

                {isDocumentationStep && hasCodeGenResult && status !== 'Completed' && (
                  <button
                    type="button"
                    className="btn-run-agent"
                    onClick={onRunDocumentation}
                    disabled={isWorkflowBusy}
                  >
                    {status === 'Failed' ? 'Retry Docs' : 'Generate Docs'}
                  </button>
                )}

                {isDocumentationStep && status === 'Completed' && (
                  <button type="button" className="btn-retry" onClick={onRunDocumentation}>
                    Regenerate
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
