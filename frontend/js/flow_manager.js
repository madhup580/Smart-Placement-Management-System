/**
 * Flow Management System
 * Makes it easy to add new flows and manage application states
 */

class FlowManager {
    constructor() {
        this.flows = new Map();
        this.currentFlow = null;
        this.flowHistory = [];
    }

    /**
     * Register a new flow
     * @param {string} name - Flow name
     * @param {object} config - Flow configuration
     */
    register(name, config) {
        this.flows.set(name, {
            name,
            steps: config.steps || [],
            onStart: config.onStart || (() => {}),
            onEnd: config.onEnd || (() => {}),
            onError: config.onError || ((error) => console.error(`[Flow:${name}] Error:`, error)),
            ...config
        });
        console.log(`[FlowManager] Registered flow: ${name}`);
    }

    /**
     * Start a flow
     */
    async start(name, data = {}) {
        const flow = this.flows.get(name);
        if (!flow) {
            console.error(`[FlowManager] Flow not found: ${name}`);
            return false;
        }

        try {
            this.currentFlow = flow;
            this.flowHistory.push({ name, started: Date.now() });
            
            console.log(`[FlowManager] Starting flow: ${name}`);
            await flow.onStart(data);
            
            // Execute steps
            for (const step of flow.steps) {
                if (typeof step === 'function') {
                    await step(data);
                } else if (step.action && typeof step.action === 'function') {
                    await step.action(data);
                    if (step.wait) {
                        await new Promise(resolve => setTimeout(resolve, step.wait));
                    }
                }
            }
            
            return true;
        } catch (error) {
            console.error(`[FlowManager] Flow error in ${name}:`, error);
            if (flow.onError) {
                flow.onError(error);
            }
            return false;
        }
    }

    /**
     * End current flow
     */
    async end(data = {}) {
        if (this.currentFlow && this.currentFlow.onEnd) {
            await this.currentFlow.onEnd(data);
        }
        this.currentFlow = null;
    }

    /**
     * Get current flow
     */
    getCurrentFlow() {
        return this.currentFlow;
    }
}

// Export singleton
window.flowManager = new FlowManager();
