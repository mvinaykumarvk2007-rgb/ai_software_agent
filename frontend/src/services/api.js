/**
 * API client service for communicating with FastAPI backend.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

/**
 * Checks backend health status.
 * @returns {Promise<{ online: boolean, data?: any, error?: string }>}
 */
export async function checkBackendHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    let response;
    try {
      response = await fetch(`${API_BASE_URL}/api/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    if (!response.ok) {
      return {
        online: false,
        error: `Server returned HTTP ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      online: true,
      data,
    };
  } catch (err) {
    return {
      online: false,
      error: err.name === 'AbortError' ? 'Connection timed out' : 'Cannot reach backend server',
    };
  }
}

/**
 * Validates project parameters with backend.
 * @param {Object} payload
 * @param {string} payload.projectName
 * @param {string} payload.requirements
 * @param {string[]} payload.selectedTechnologies
 * @returns {Promise<{ success: boolean, data?: any, error?: string }>}
 */
export async function validateProject({ projectName, requirements, selectedTechnologies }) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/projects/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        project_name: projectName,
        requirements: requirements,
        selected_technologies: selectedTechnologies,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      let errorMsg = 'Validation failed';
      if (data.detail) {
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((d) => d.msg || d.message).join('; ');
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        }
      }
      return {
        success: false,
        error: errorMsg,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to communicate with backend validation service.',
    };
  }
}

/**
 * Executes Agent 1: Requirement Analysis.
 * @param {Object} payload
 * @param {string} payload.projectName
 * @param {string} payload.requirements
 * @param {string[]} payload.selectedTechnologies
 * @returns {Promise<{ success: boolean, data?: any, error?: string, status?: number }>}
 */
export async function runRequirementAnalysis({ projectName, requirements, selectedTechnologies }) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agents/requirement-analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        project_name: projectName,
        requirements: requirements,
        selected_technologies: selectedTechnologies,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      let errorMsg = 'Requirement analysis failed.';
      if (data.detail) {
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((d) => d.msg || d.message).join('; ');
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        }
      }
      return {
        success: false,
        status: response.status,
        error: errorMsg,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to reach the Requirement Analysis agent endpoint.',
    };
  }
}

/**
 * Executes Agent 2: Development Planning.
 * @param {Object} requirementAnalysis - Validated RequirementAnalysisResult from Agent 1
 * @returns {Promise<{ success: boolean, data?: any, error?: string, status?: number }>}
 */
export async function runDevelopmentPlanning(requirementAnalysis) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agents/development-planning`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        requirement_analysis: requirementAnalysis,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      let errorMsg = 'Development planning failed.';
      if (data.detail) {
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((d) => d.msg || d.message).join('; ');
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        }
      }
      return {
        success: false,
        status: response.status,
        error: errorMsg,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to reach the Development Planning agent endpoint.',
    };
  }
}

/**
 * Executes Agent 3: Code Generation.
 * @param {Object} payload
 * @param {string} payload.projectName
 * @param {string} payload.requirements
 * @param {string[]} payload.selectedTechnologies
 * @param {Object} payload.requirementAnalysis
 * @param {Object} payload.developmentPlan
 * @returns {Promise<{ success: boolean, data?: any, error?: string, status?: number }>}
 */
export async function runCodeGeneration({
  projectName,
  requirements,
  selectedTechnologies,
  requirementAnalysis,
  developmentPlan,
}) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agents/code-generation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        project_name: projectName,
        requirements: requirements,
        selected_technologies: selectedTechnologies,
        requirement_analysis: requirementAnalysis,
        development_plan: developmentPlan,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      let errorMsg = 'Code generation failed.';
      if (data.detail) {
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((d) => d.msg || d.message).join('; ');
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        }
      }
      return {
        success: false,
        status: response.status,
        error: errorMsg,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to communicate with the Code Generation agent endpoint.',
    };
  }
}

/**
 * Executes Agent 4: Testing Agent.
 * @param {string} projectId
 * @returns {Promise<{ success: boolean, data?: any, error?: string, status?: number }>}
 */
export async function runProjectTests(projectId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/test`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        status: response.status,
        error: data.detail || 'Project verification checks failed.',
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to reach the Testing agent endpoint.',
    };
  }
}

export async function runProjectDebugging(projectId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/debug`,
      { method: 'POST', headers: { 'Accept': 'application/json' } },
    );
    const data = await response.json();
    if (!response.ok) {
      return { success: false, status: response.status, error: data.detail || 'Project debugging failed.' };
    }
    return { success: true, data };
  } catch {
    return { success: false, error: 'Network error: Failed to reach the Debugging agent endpoint.' };
  }
}

export async function generateProjectDocumentation(projectId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/documentation`,
      { method: 'POST', headers: { 'Accept': 'application/json' } },
    );
    const data = await response.json();
    if (!response.ok) {
      return { success: false, status: response.status, error: data.detail || 'Documentation generation failed.' };
    }
    return { success: true, data };
  } catch {
    return { success: false, error: 'Network error: Failed to reach the Documentation agent endpoint.' };
  }
}

export async function startProjectPreview(projectId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/preview`,
      { method: 'POST', headers: { 'Accept': 'application/json' } },
    );
    const data = await response.json();
    if (!response.ok) {
      return { success: false, status: response.status, error: data.detail || 'Could not start website preview.' };
    }
    return { success: true, data };
  } catch {
    return { success: false, error: 'Network error: Failed to start the website preview.' };
  }
}

export async function stopProjectPreview(projectId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/preview`,
      { method: 'DELETE', headers: { 'Accept': 'application/json' } },
    );
    const data = await response.json();
    if (!response.ok) {
      return { success: false, status: response.status, error: data.detail || 'Could not stop website preview.' };
    }
    return { success: true, data };
  } catch {
    return { success: false, error: 'Network error: Failed to stop the website preview.' };
  }
}

/**
 * Retrieves the latest test report for a generated project.
 * @param {string} projectId
 * @returns {Promise<{ success: boolean, data?: any, error?: string }>}
 */
export async function getProjectTestReport(projectId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/test-report`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || 'Failed to retrieve test report.',
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to load test report.',
    };
  }
}

/**
 * Fetches content of a specific generated file.
 * @param {string} projectId
 * @param {string} filePath
 * @returns {Promise<{ success: boolean, data?: { path: string, content: string, size_bytes: number }, error?: string }>}
 */
export async function getProjectFileContent(projectId, filePath) {
  try {
    const encodedPath = filePath.split('/').map(encodeURIComponent).join('/');
    const response = await fetch(`${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/files/${encodedPath}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || 'Failed to load file content.',
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: 'Network error: Failed to read file content.',
    };
  }
}

/**
 * Returns the download URL for the project ZIP archive.
 * @param {string} projectId
 * @returns {string}
 */
export function getProjectZipDownloadUrl(projectId) {
  return `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/download`;
}
