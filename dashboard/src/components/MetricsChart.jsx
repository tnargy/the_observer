import React, { useState, useEffect } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { api } from '../utils/api'

export function MetricsChart({ agentId }) {
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        api.getAgentMetrics(agentId, 1)
            .then(metrics => {
                const formatted = metrics.map(m => ({
                    timestamp: m.timestamp * 1000,
                    time: new Date(m.timestamp * 1000).toLocaleTimeString(),
                    cpu: m.cpu_percent,
                    memory: m.memory_percent,
                    disk: m.disk_percent,
                    networkIn: m.network_in_bytes_per_sec,
                    networkOut: m.network_out_bytes_per_sec
                }))
                setData(formatted)
            })
            .catch(()=> setData([]))
            .finally(()=> setLoading(false))
    }, [agentId])

    if (loading) return <div>Loading chart...</div>
    if (!data || data.length === 0) return <div>No data yet</div>

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-white mb-2">CPU Usage</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis domain={[0, 100]} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Line type="monotone" dataKey="cpu" stroke="#3B82F6" dot={false} isAnimationActive={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div>
                <h3 className="text-white mb-2">Memory Usage</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis domain={[0, 100]} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Line type="monotone" dataKey="memory" stroke="#10B981" dot={false} isAnimationActive={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div>
                <h3 className="text-white mb-2">Disk Usage</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis domain={[0, 100]} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Line type="monotone" dataKey="disk" stroke="#F59E0B" dot={false} isAnimationActive={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div>
                <h3 className="text-white mb-2">Network I/O</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Legend />
                        <Line type="monotone" dataKey="networkIn" stroke="#06B6D4" name="Download" dot={false} isAnimationActive={false} />
                        <Line type="monotone" dataKey="networkOut" stroke="#EC4899" name="Upload" dot={false} isAnimationActive={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}
