export function formatBytes(bytes){
  if(!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B','KB','MB','GB']
  const i = Math.floor(Math.log(bytes)/Math.log(k))
  return Math.round(bytes/Math.pow(k,i)*100)/100 + ' ' + sizes[i]
}

export function formatTime(isoString){
  if(!isoString) return 'N/A'
  const date = new Date(isoString)
  const now = new Date()
  const diff = Math.floor((now - date)/1000)
  if(diff < 10) return 'Just now'
  if(diff < 60) return `${diff}s ago`
  if(diff < 3600) return `${Math.floor(diff/60)}m ago`
  if(diff < 86400) return `${Math.floor(diff/3600)}h ago`
  return date.toLocaleDateString()
}

export function formatPercent(value){
  return (value || value === 0) ? `${value.toFixed(1)}%` : 'N/A'
}
