import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';

import { SymbolNode, FileNode } from './components/CustomNodes';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { DetailsPanel } from './components/DetailsPanel';
import { ActivityTimeline } from './components/ActivityTimeline';
import { RepoStatus, SymbolNodeData, ChangeEvent } from './types';

const nodeTypes = {
  symbolNode: SymbolNode,
  fileNode: FileNode,
};

function FlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onNodeClick,
  filterStatus,
  searchQuery,
}: {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: any;
  onEdgesChange: any;
  onNodeClick: (node: Node) => void;
  filterStatus: string;
  searchQuery: string;
}) {
  const { fitView } = useReactFlow();

  // Filter and highlight nodes based on search and status
  const filteredNodes = useMemo(() => {
    return nodes.map((node) => {
      const data = node.data as unknown as SymbolNodeData;
      let isVisible = true;

      if (filterStatus !== 'all' && node.type === 'symbolNode') {
        if (data.status !== filterStatus) {
          isVisible = false;
        }
      }

      if (searchQuery.trim() && node.type === 'symbolNode') {
        const q = searchQuery.toLowerCase();
        const matchesName = data.name.toLowerCase().includes(q);
        const matchesSig = data.signature?.toLowerCase().includes(q) ?? false;
        if (!matchesName && !matchesSig) {
          isVisible = false;
        }
      }

      return {
        ...node,
        style: {
          ...node.style,
          opacity: isVisible ? 1 : 0.15,
          pointerEvents: (isVisible ? 'auto' : 'none') as React.CSSProperties['pointerEvents'],
        },
      };
    });
  }, [nodes, filterStatus, searchQuery]);

  return (
    <div className="flex-1 h-[calc(100vh-3.5rem)] relative bg-[#0d1117]">
      <ReactFlow
        nodes={filteredNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick(node)}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2.5}
      >
        <Background color="#30363d" gap={20} size={1} />
        <Controls className="!bg-slate-800 !border-slate-700 !text-slate-300" />
        <MiniMap
          nodeColor={(n) => {
            if (n.type === 'fileNode') return '#38bdf8';
            const status = (n.data as unknown as SymbolNodeData).status;
            switch (status) {
              case 'added': return '#3fb950';
              case 'modified': return '#d29922';
              case 'deleted': return '#f85149';
              case 'impacted': return '#bc8cff';
              default: return '#64748b';
            }
          }}
          className="!bg-slate-900 !border-slate-800"
        />
      </ReactFlow>
    </div>
  );
}

export function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [status, setStatus] = useState<RepoStatus | null>(null);
  const [files, setFiles] = useState<Array<{ path: string; language: string; symbol_count: number }>>([]);
  const [events, setEvents] = useState<ChangeEvent[]>([]);
  const [selectedNodeData, setSelectedNodeData] = useState<SymbolNodeData | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [scanning, setScanning] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  // Fetch initial graph and status
  const fetchGraph = useCallback(async () => {
    try {
      const [resFlow, resStatus, resFiles, resEvents] = await Promise.all([
        fetch('/api/graph/flow').then((r) => r.json()),
        fetch('/api/status').then((r) => r.json()),
        fetch('/api/files').then((r) => r.json()),
        fetch('/api/events').then((r) => r.json()),
      ]);

      setNodes(resFlow.nodes || []);
      setEdges(resFlow.edges || []);
      setStatus(resStatus);
      setFiles(resFiles || []);
      setEvents(resEvents || []);
    } catch (e) {
      console.error('Failed to fetch CodePulse graph data:', e);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // WebSocket live streaming
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/events`;

    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout>;

    const connectWs = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'symbols_changed') {
            // Live update triggered by watcher!
            fetchGraph();
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        retryTimer = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connectWs();

    return () => {
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, [fetchGraph]);

  const handleScan = async () => {
    setScanning(true);
    try {
      await fetch('/api/scan', { method: 'POST' });
      await fetchGraph();
    } finally {
      setScanning(false);
    }
  };

  const handleNodeClick = (node: Node) => {
    if (node.type === 'symbolNode') {
      setSelectedNodeData(node.data as unknown as SymbolNodeData);
    }
  };

  const handleSelectFile = (filePath: string) => {
    setSelectedFile(filePath);
    // Find first symbol of this file to focus
    const match = nodes.find(
      (n) => n.type === 'symbolNode' && (n.data as unknown as SymbolNodeData).file_path === filePath
    );
    if (match) {
      setSelectedNodeData(match.data as unknown as SymbolNodeData);
    }
  };

  const handleFocusSymbol = (symbolId: string) => {
    const match = nodes.find((n) => n.id === symbolId);
    if (match) {
      setSelectedNodeData(match.data as unknown as SymbolNodeData);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#0d1117] text-[#c9d1d9]">
      <Header
        status={status}
        wsConnected={wsConnected}
        filterStatus={filterStatus}
        onFilterChange={setFilterStatus}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onScan={handleScan}
        scanning={scanning}
        timelineOpen={timelineOpen}
        onToggleTimeline={() => setTimelineOpen((prev) => !prev)}
      />

      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar
          status={status}
          files={files}
          selectedFile={selectedFile}
          onSelectFile={handleSelectFile}
        />

        <ReactFlowProvider>
          <FlowCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            filterStatus={filterStatus}
            searchQuery={searchQuery}
          />
        </ReactFlowProvider>

        {selectedNodeData && (
          <DetailsPanel
            selectedNode={selectedNodeData}
            onClose={() => setSelectedNodeData(null)}
            onFocusSymbol={handleFocusSymbol}
          />
        )}
      </div>

      <ActivityTimeline
        events={events}
        isOpen={timelineOpen}
        onClose={() => setTimelineOpen(false)}
      />
    </div>
  );
}

export default App;
