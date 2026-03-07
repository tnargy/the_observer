import React, { useEffect, useState } from 'react'
import { api } from '../utils/api'
import { ServerCard } from '../components/ServerCard'
import { useSocket } from '../hooks/useSocket'
import { useNavigate } from 'react-router-dom'

export default function Dashboard(){
  const [agents, setAgents] = useState([])
  const [error, setError] = useState(null)
  const { socket } = useSocket()
  const navigate = useNavigate()

  useEffect(()=>{
    let mounted = true
    api.getAgents()
      .then(data => mounted && setAgents(data))
      .catch(e => mounted && setError('Failed to load agents'))
    return ()=>{ mounted = false }
  },[])

  useEffect(()=>{
    if(!socket) return
    socket.on('metric_update', (data)=>{
      setAgents(prev => {
        const idx = prev.findIndex(a => a.id === data.agent_id)
        if(idx === -1){
          // add
          return [{ id: data.agent_id, status: data.status, last_seen: new Date().toISOString(), metrics: data.metrics }, ...prev]
        }
        const copy = [...prev]
        const existing = copy[idx]
        copy[idx] = { ...existing, status: data.status, last_seen: new Date().toISOString(), metrics: data.metrics }
        return copy
      })
    })

    return ()=> socket.off('metric_update')
  },[socket])

  return (
    <div>
      <h2 className="text-2xl mb-4">Fleet Overview</h2>
      {error && <div className="text-red-400">{error}</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map(agent => (
          <ServerCard key={agent.id} agent={agent} onClick={()=>navigate(`/agent/${agent.id}`)} />
        ))}
      </div>
    </div>
  )
}
