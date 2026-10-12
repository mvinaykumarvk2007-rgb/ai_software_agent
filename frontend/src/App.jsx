import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import TechSelector from './components/TechSelector';
import WorkflowPanel from './components/WorkflowPanel';
import ResultsArea from './components/ResultsArea';
import {
  checkBackendHealth,
  validateProject,
  runRequirementAnalysis,
  runDevelopmentPlanning,
  runCodeGeneration,
  runProjectTests,
  runProjectDebugging,
  generateProjectDocumentation,
  startProjectPreview,
  stopProjectPreview,
  getProjectFileContent,
} from './services/api';
import './App.css';

export default function App() {
  const [projectName, setProjectName] = useState('E-Commerce Inventory Manager');
  const [requirements, setRequirements] = useState(
    'Build a full-stack inventory management system with product listings, stock levels, and automated restock alerts.'
  );
  const [selectedTechnologies, setSelectedTechnologies] = useState(['React', 'Python', 'SQLite']);

  // Connection & Form states
  const [isOnline, setIsOnline] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [activeError, setActiveError] = useState(null);

  // Workflow & Agent Results
  const [workflowStatus, setWorkflowStatus] = useState({
    'Requirement Analysis': 'Not started',
    'Planning': 'Not started',
    'Code Generation': 'Not started',
    'Testing': 'Not started',
    'Website Preview': 'Not started',
    'Debugging': 'Not started',
    'Documentation': 'Not started',
  });

  const [validationResult, setValidationResult] = useState(null);
  const [requirementResult, setRequirementResult] = useState(null);
  const [planningResult, setPlanningResult] = useState(null);
  const [codeGenResult, setCodeGenResult] = useState(null);
  const [testReport, setTestReport] = useState(null);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [debugReport, setDebugReport] = useState(null);
  const [documentation, setDocumentation] = useState(null);

  // File previewer state
  const [activeFilePath, setActiveFilePath] = useState(null);
  const [activeFileContent, setActiveFileContent] = useState(null);
  const isWorkflowBusy = Object.values(workflowStatus).some((status) =>
    ['Analyzing...', 'Planning...', 'Generating Code...', 'Running Tests...', 'Starting Preview...', 'Running Debugging...', 'Generating Documentation...'].includes(status)
  );

  // Health check polling
  const performHealthCheck = useCallback(async () => {
    setIsChecking(true);
    const result = await checkBackendHealth();
    setIsOnline(result.online);
    setIsChecking(false);
  }, []);

  useEffect(() => {
    performHealthCheck();
    const interval = setInterval(performHealthCheck, 10000);
    return () => clearInterval(interval);
  }, [performHealthCheck]);

  // Handler for Agent 1: Requirement Analysis
  const executeRequirementAnalysis = async (name, reqs, techs) => {
    setWorkflowStatus((prev) => ({
      ...prev,
      'Requirement Analysis': 'Analyzing...',
      'Planning': 'Not started',
      'Code Generation': 'Not started',
      'Testing': 'Not started',
      'Debugging': 'Not started',
      'Documentation': 'Not started',
    }));
    setActiveError(null);
    setRequirementResult(null);
    setPlanningResult(null);
    setCodeGenResult(null);
    setTestReport(null);
    setDebugReport(null);
    setDocumentation(null);
    setPreviewInfo(null);
    setWorkflowStatus((prev) => ({ ...prev, 'Website Preview': 'Not started' }));
    setActiveFilePath(null);
    setActiveFileContent(null);

    const res = await runRequirementAnalysis({
      projectName: name,
      requirements: reqs,
      selectedTechnologies: techs,
    });

    if (res.success) {
      setRequirementResult(res.data);
      setWorkflowStatus((prev) => ({
        ...prev,
        'Requirement Analysis': 'Completed',
      }));
      return res.data;
    } else {
      setWorkflowStatus((prev) => ({
        ...prev,
        'Requirement Analysis': 'Failed',
      }));
      setActiveError(res.error || 'Failed to complete requirement analysis.');
      return null;
    }
  };

  // Handler for Agent 2: Development Planning
  const executePlanning = async (sourceRequirements = requirementResult) => {
    if (!sourceRequirements) {
      setActiveError('Cannot run planning agent without completed requirement analysis.');
      return null;
    }

    setWorkflowStatus((prev) => ({
      ...prev,
      'Planning': 'Planning...',
      'Code Generation': 'Not started',
      'Testing': 'Not started',
      'Website Preview': 'Not started',
      'Debugging': 'Not started',
      'Documentation': 'Not started',
    }));
    setActiveError(null);
    setPlanningResult(null);
    setCodeGenResult(null);
    setTestReport(null);
    setDebugReport(null);
    setDocumentation(null);
    setActiveFilePath(null);
    setActiveFileContent(null);

    const res = await runDevelopmentPlanning(sourceRequirements);

    if (res.success) {
      setPlanningResult(res.data);
      setWorkflowStatus((prev) => ({
        ...prev,
        'Planning': 'Completed',
      }));
      return res.data;
    } else {
      setWorkflowStatus((prev) => ({
        ...prev,
        'Planning': 'Failed',
      }));
      setActiveError(res.error || 'Failed to generate development plan.');
      return null;
    }
  };

  // Handler for Agent 3: Code Generation
  const executeCodeGeneration = async (options = {}) => {
    const sourceRequirements = options.requirementAnalysis || requirementResult;
    const sourcePlan = options.developmentPlan || planningResult;
    if (!sourceRequirements || !sourcePlan) {
      setActiveError('Cannot generate code without completed requirement analysis and development plan.');
      return null;
    }

    setWorkflowStatus((prev) => ({
      ...prev,
      'Code Generation': 'Generating Code...',
      'Testing': 'Not started',
      'Website Preview': 'Not started',
      'Debugging': 'Not started',
      'Documentation': 'Not started',
    }));
    setActiveError(null);
    setTestReport(null);
    setDebugReport(null);
    setDocumentation(null);
    setPreviewInfo(null);
    setCodeGenResult(null);
    setActiveFilePath(null);
    setActiveFileContent(null);

    const res = await runCodeGeneration({
      projectName: options.projectName || projectName.trim(),
      requirements: options.requirements || requirements.trim(),
      selectedTechnologies: options.selectedTechnologies || selectedTechnologies,
      requirementAnalysis: sourceRequirements,
      developmentPlan: sourcePlan,
    });

    if (res.success) {
      setCodeGenResult(res.data);
      setWorkflowStatus((prev) => ({
        ...prev,
        'Code Generation': 'Completed',
      }));

      // Select default file for preview
      if (res.data.files && res.data.files.length > 0) {
        const preferred = res.data.files.find((f) => f.path.includes('App.jsx')) || res.data.files[0];
        setActiveFilePath(preferred.path);
        setActiveFileContent(preferred.content);
      }
      return res.data;
    } else {
      setWorkflowStatus((prev) => ({
        ...prev,
        'Code Generation': 'Failed',
      }));
      setActiveError(res.error || 'Failed to generate project code.');
      return null;
    }
  };

  // Handler for Agent 4: Testing Agent
  const executeTesting = async (projectId = codeGenResult && codeGenResult.project_id) => {
    if (!projectId) {
      setActiveError('Cannot run verification tests without a generated project.');
      return null;
    }

    setWorkflowStatus((prev) => ({
      ...prev,
      'Testing': 'Running Tests...',
    }));
    setActiveError(null);
    setTestReport(null);

    const res = await runProjectTests(projectId);

    if (res.success) {
      setTestReport(res.data);
      const isFailed = res.data.summary && res.data.summary.failed > 0;
      setWorkflowStatus((prev) => ({
        ...prev,
        'Testing': isFailed ? 'Failed' : 'Completed',
      }));
      return res.data;
    } else {
      setWorkflowStatus((prev) => ({
        ...prev,
        'Testing': 'Failed',
      }));
      setActiveError(res.error || 'Failed to complete project verification tests.');
      return null;
    }
  };

  const executePreview = async (projectId = codeGenResult && codeGenResult.project_id) => {
    if (!projectId) {
      setActiveError('Cannot preview a website before code generation is complete.');
      return null;
    }

    setWorkflowStatus((prev) => ({ ...prev, 'Website Preview': 'Starting Preview...' }));
    setPreviewInfo({ status: 'starting' });
    setActiveError(null);
    const res = await startProjectPreview(projectId);
    if (res.success) {
      setPreviewInfo(res.data);
      setWorkflowStatus((prev) => ({ ...prev, 'Website Preview': 'Completed' }));
      return res.data;
    }

    const failure = { status: 'failed', error: res.error || 'Could not start the website preview.' };
    setPreviewInfo(failure);
    setWorkflowStatus((prev) => ({ ...prev, 'Website Preview': 'Failed' }));
    setActiveError(failure.error);
    return null;
  };

  const executeStopPreview = async () => {
    if (!codeGenResult || !codeGenResult.project_id) return;
    const res = await stopProjectPreview(codeGenResult.project_id);
    if (res.success) {
      setPreviewInfo({ ...res.data });
      setWorkflowStatus((prev) => ({ ...prev, 'Website Preview': 'Not started' }));
      setActiveError(null);
    } else {
      setActiveError(res.error || 'Could not stop the website preview.');
    }
  };

  const executeDebugging = async (projectId = codeGenResult && codeGenResult.project_id) => {
    if (!projectId) {
      setActiveError('Cannot debug before code generation is complete.');
      return null;
    }
    setWorkflowStatus((prev) => ({ ...prev, Debugging: 'Running Debugging...' }));
    setActiveError(null);
    setDebugReport(null);
    const res = await runProjectDebugging(projectId);
    if (res.success) {
      setDebugReport(res.data);
      setWorkflowStatus((prev) => ({ ...prev, Debugging: 'Completed' }));
      return res.data;
    }
    setWorkflowStatus((prev) => ({ ...prev, Debugging: 'Failed' }));
    setActiveError(res.error || 'Project debugging failed.');
    return null;
  };

  const executeDocumentation = async (
    projectId = codeGenResult && codeGenResult.project_id,
    { preserveError = false } = {},
  ) => {
    if (!projectId) {
      setActiveError('Cannot generate documentation before code generation is complete.');
      return null;
    }
    setWorkflowStatus((prev) => ({ ...prev, Documentation: 'Generating Documentation...' }));
    setDocumentation(null);
    const res = await generateProjectDocumentation(projectId);
    if (res.success) {
      setDocumentation(res.data);
      setCodeGenResult((previous) => previous ? {
        ...previous,
        manifest: res.data.manifest,
      } : previous);
      setWorkflowStatus((prev) => ({ ...prev, Documentation: 'Completed' }));
      if (!preserveError) setActiveError(null);
      return res.data;
    }
    setWorkflowStatus((prev) => ({ ...prev, Documentation: 'Failed' }));
    setActiveError(res.error || 'Documentation generation failed.');
    return null;
  };

  // Handler for selecting a file in the project explorer
  const handleSelectFile = async (filePath) => {
    setActiveFilePath(filePath);
    setActiveFileContent(null);
    setActiveError(null);

    // If file content is already in codeGenResult files array, use it directly
    if (codeGenResult && codeGenResult.files) {
      const match = codeGenResult.files.find((f) => f.path === filePath);
      if (match) {
        setActiveFileContent(match.content);
        return;
      }
    }

    // Otherwise, fetch from backend
    if (codeGenResult && codeGenResult.project_id) {
      const res = await getProjectFileContent(codeGenResult.project_id, filePath);
      if (res.success) {
        setActiveFileContent(res.data.content);
      } else {
        setActiveError(res.error || 'Failed to load the selected file.');
      }
    }
  };

  // Initial Form Submit
  const handleStartDevelopment = async (e) => {
    e.preventDefault();
    setFormError(null);
    setActiveError(null);

    const cleanName = projectName.trim();
    const cleanReqs = requirements.trim();

    if (!cleanName) {
      setFormError('Please enter a project name.');
      return;
    }
    if (cleanReqs.length < 10) {
      setFormError('Requirements must be at least 10 characters long.');
      return;
    }
    setIsSubmitting(true);
    setValidationResult(null);

    // 1. Validate with backend
    const valRes = await validateProject({
      projectName: cleanName,
      requirements: cleanReqs,
      selectedTechnologies,
    });

    if (!valRes.success) {
      setIsSubmitting(false);
      setFormError(valRes.error || 'Validation failed.');
      return;
    }

    setValidationResult(valRes.data);

    if (previewInfo?.status === 'running' && codeGenResult?.project_id) {
      const stopped = await stopProjectPreview(codeGenResult.project_id);
      if (!stopped.success) {
        setIsSubmitting(false);
        setActiveError(stopped.error || 'Could not stop the previous website preview.');
        return;
      }
    }
    setIsSubmitting(false);

    const analysis = await executeRequirementAnalysis(cleanName, cleanReqs, selectedTechnologies);
    if (!analysis) return;
    const plan = await executePlanning(analysis);
    if (!plan) return;
    const generated = await executeCodeGeneration({
      projectName: cleanName,
      requirements: cleanReqs,
      selectedTechnologies,
      requirementAnalysis: analysis,
      developmentPlan: plan,
    });
    if (!generated) return;
    const report = await executeTesting(generated.project_id);
    if (!report) return;
    await executePreview(generated.project_id);
    const debugging = await executeDebugging(generated.project_id);
    await executeDocumentation(generated.project_id, { preserveError: !debugging });
  };

  return (
    <div className="dashboard-container" id="dashboard">
      <Sidebar />

      <main className="app-main">
        <Header
          isOnline={isOnline}
          isChecking={isChecking}
          onRefresh={performHealthCheck}
        />

        <div className="dashboard-content">
          {/* Left Column: Project Form */}
          <div className="dashboard-card" id="project-form">
            <div className="card-header">
              <h2 className="card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                Project Specification
              </h2>
              <p className="card-subtitle">
                Describe the app you want. The agents will build, test, and show you a website.
              </p>
            </div>

            <form onSubmit={handleStartDevelopment}>
              <div className="form-group">
                <label className="form-label" htmlFor="projectName">
                  Project Name <span className="req">*</span>
                </label>
                <input
                  id="projectName"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Real-Time Chat Engine"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  maxLength={100}
                  disabled={isWorkflowBusy || isSubmitting}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="requirements">
                  Project Requirements <span className="req">*</span>
                </label>
                <textarea
                  id="requirements"
                  className="form-textarea"
                  placeholder="Describe key features, database models, user flows, and goals..."
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  disabled={isWorkflowBusy || isSubmitting}
                />
                <div className="form-hint">
                  {requirements.length} characters (minimum 10 required)
                </div>
              </div>

              <TechSelector
                selectedTechnologies={selectedTechnologies}
                onChange={setSelectedTechnologies}
                disabled={isWorkflowBusy || isSubmitting}
              />

              <button
                type="submit"
                className="btn-primary"
                disabled={isSubmitting || isWorkflowBusy}
              >
                {isSubmitting || isWorkflowBusy ? (
                  <>
                    <svg className="spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="16"></circle>
                    </svg>
                    Agents are building your website...
                  </>
                ) : (
                  <>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                    Build My Website
                  </>
                )}
              </button>

              {formError && (
                <div className="alert-box alert-error" role="alert">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                  <div>{formError}</div>
                </div>
              )}
            </form>
          </div>

          {/* Right Column: Workflow Timeline & Results Console */}
          <div className="dashboard-card" id="agents">
            <div className="card-header">
              <h2 className="card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                </svg>
                Autonomous Agent Workflow
              </h2>
              <p className="card-subtitle">
                Follow the agents as they turn your idea into a tested, viewable website.
              </p>
            </div>

            <WorkflowPanel
              workflowStatus={workflowStatus}
              onRunRequirementAnalysis={() =>
                executeRequirementAnalysis(projectName.trim(), requirements.trim(), selectedTechnologies)
              }
              onRunPlanning={() => executePlanning()}
              onRunCodeGeneration={() => executeCodeGeneration()}
              onRunTesting={() => executeTesting()}
              onRunDebugging={() => executeDebugging()}
              onRunDocumentation={() => executeDocumentation()}
              onRunPreview={executePreview}
              previewInfo={previewInfo}
              onStopPreview={executeStopPreview}
              isWorkflowBusy={isWorkflowBusy}
              hasRequirementResult={Boolean(requirementResult)}
              hasPlanningResult={Boolean(planningResult)}
              hasCodeGenResult={Boolean(codeGenResult && codeGenResult.project_id)}
            />

            <ResultsArea
              requirementResult={requirementResult}
              planningResult={planningResult}
              codeGenResult={codeGenResult}
              testReport={testReport}
              debugReport={debugReport}
              documentation={documentation}
              previewInfo={previewInfo}
              onRunPreview={executePreview}
              onStopPreview={executeStopPreview}
              isWorkflowBusy={isWorkflowBusy}
              onRunTesting={() => executeTesting()}
              onRunDebugging={() => executeDebugging()}
              onRunDocumentation={() => executeDocumentation()}
              activeFilePath={activeFilePath}
              activeFileContent={activeFileContent}
              onSelectFile={handleSelectFile}
              validationResult={validationResult}
              activeError={activeError}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
