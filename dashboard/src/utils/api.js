const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

export const api = {
  getAgents: async () => {
    const response = await fetch(`${API_URL}/api/agents`)
    if(!response.ok) throw new Error('Failed to fetch agents')
    return response.json()
  },

  getAgentMetrics: async (agentId, hours = 1) => {
    const response = await fetch(`${API_URL}/api/agents/${agentId}/metrics?hours=${hours}`)
    if(!response.ok) throw new Error('Failed to fetch metrics')
    return response.json()
  }
}
