import React from 'react'
import { formatBytes, formatTime } from '../utils/formatters'

export function ServerCard({ agent, onClick }) {
    const isOnline = agent.status === 'online'
    const metrics = agent.metrics || {}

    return (
        <div
            onClick={onClick}
            className={`p-4 rounded border cursor-pointer transition ${isOnline ? 'bg-slate-700 border-slate-600 hover:border-blue-500' : 'bg-slate-800 border-slate-700'}`}>
            <div className="flex justify-between items-center mb-2">
                <h3 className="text-lg font-bold text-white">{agent.id}</h3>
                <span className={`inline-block w-3 h-3 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}></span>
            </div>

            <div className="text-sm text-gray-400 mb-3">Last seen: {formatTime(agent.last_seen)}</div>

            {isOnline ? (
                <div className="space-y-1 text-sm text-gray-300">
                    <div>CPU: {metrics.cpu_percent?.toFixed ? metrics.cpu_percent.toFixed(1) : 'N/A'}%</div>
                    <div>RAM: {metrics.memory_percent?.toFixed ? metrics.memory_percent.toFixed(1) : 'N/A'}%</div>
                    <div>Disk: {metrics.disk_percent?.toFixed ? metrics.disk_percent.toFixed(1) : 'N/A'}%</div>
                    <div className="text-xs text-gray-400 mt-2">
                        ↓ {formatBytes(metrics.network_in_bytes_per_sec || 0)}/s {' '}
                        ↑ {formatBytes(metrics.network_out_bytes_per_sec || 0)}/s
                    </div>
                </div>
            ) : (
                <div className="text-sm text-gray-500">No data</div>
            )}
        </div>
    );
}
