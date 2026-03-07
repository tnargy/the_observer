import React from 'react'
import { useParams } from 'react-router-dom'
import { MetricsChart } from '../components/MetricsChart'

export default function ServerDetail(){
  const { id } = useParams()
  return (
    <div>
      <h2 className="text-2xl mb-4">Agent: {id}</h2>
      <MetricsChart agentId={id} />
    </div>
  )
}
