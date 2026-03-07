import { useEffect, useState } from 'react'
import { io } from 'socket.io-client'

export function useSocket(){
  const [socket, setSocket] = useState(null)
  const [connected, setConnected] = useState(false)

  useEffect(()=>{
    const newSocket = io(import.meta.env.VITE_API_URL || 'http://localhost:5000', {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5
    })

    newSocket.on('connect', ()=> setConnected(true))
    newSocket.on('disconnect', ()=> setConnected(false))

    setSocket(newSocket)
    return ()=> newSocket.close()
  },[])

  return { socket, connected }
}
