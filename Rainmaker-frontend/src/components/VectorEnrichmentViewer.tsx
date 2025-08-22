import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface VectorInsight {
  content: string;
  source_type: string;
  similarity: number;
  source_url: string;
}

interface EnrichmentUpdate {
  type: string;
  workflow_id: string;
  step: string;
  reasoning: string;
  status: 'active' | 'complete' | 'fully_complete';
  timestamp: string;
  data?: {
    citations_count?: number;
    stored_chunks?: number;
    insight_categories?: number;
    total_insights?: number;
    research_summary?: any;
    analysis_depth?: string;
    insights_used?: number;
    research_chunks?: number;
  };
}

interface VectorEnrichmentViewerProps {
  workflowId: string;
  prospectName: string;
}

export const VectorEnrichmentViewer: React.FC<VectorEnrichmentViewerProps> = ({
  workflowId,
  prospectName
}) => {
  const [updates, setUpdates] = useState<EnrichmentUpdate[]>([]);
  const [currentPhase, setCurrentPhase] = useState<string>('Starting');
  const [totalChunks, setTotalChunks] = useState(0);
  const [semanticQueries, setSemanticQueries] = useState<string[]>([]);
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [insightCategories, setInsightCategories] = useState(0);

  useEffect(() => {
    // WebSocket connection for real-time updates
    const ws = new WebSocket(`ws://localhost:8000/ws/enrichment/${workflowId}`);
    
    ws.onmessage = (event) => {
      const update: EnrichmentUpdate = JSON.parse(event.data);
      handleEnrichmentUpdate(update);
    };

    return () => ws.close();
  }, [workflowId]);

  const handleEnrichmentUpdate = (update: EnrichmentUpdate) => {
    setUpdates(prev => [...prev, update]);

    // Update phase tracking
    if (update.step.includes('Discovery') || update.step.includes('Research')) {
      setCurrentPhase('discovery');
    } else if (update.step.includes('Storing') || update.step.includes('Storage')) {
      setCurrentPhase('storage');
      if (update.data?.stored_chunks) {
        setTotalChunks(prev => prev + update.data.stored_chunks);
      }
    } else if (update.step.includes('Semantic') || update.step.includes('Vector')) {
      setCurrentPhase('analysis');
      if (update.reasoning.includes('Searching for insights about:')) {
        const query = update.reasoning.split('Searching for insights about: ')[1];
        setCurrentQuery(query);
        setSemanticQueries(prev => [...prev, query]);
      }
      if (update.data?.insight_categories) {
        setInsightCategories(update.data.insight_categories);
      }
    } else if (update.step.includes('AI Analysis') || update.step.includes('Enhanced')) {
      setCurrentPhase('synthesis');
    }
  };

  const getPhaseProgress = () => {
    const phases = ['discovery', 'storage', 'analysis', 'synthesis'];
    const currentIndex = phases.indexOf(currentPhase);
    return ((currentIndex + 1) / phases.length) * 100;
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">
          🧠 Vector-Powered Analysis: {prospectName}
        </h2>
        <div className="mt-2 bg-gray-200 rounded-full h-2">
          <motion.div
            className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${getPhaseProgress()}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Phase Indicators */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { name: 'Discovery', icon: '🔍', phase: 'discovery' },
          { name: 'Storage', icon: '💾', phase: 'storage' },
          { name: 'Analysis', icon: '🎯', phase: 'analysis' },
          { name: 'Synthesis', icon: '🤖', phase: 'synthesis' }
        ].map((phaseInfo) => (
          <motion.div
            key={phaseInfo.phase}
            className={`p-3 rounded-lg text-center ${
              currentPhase === phaseInfo.phase
                ? 'bg-blue-100 border-2 border-blue-500'
                : updates.some(u => u.step.toLowerCase().includes(phaseInfo.phase))
                ? 'bg-green-100 border-2 border-green-500'
                : 'bg-gray-100 border-2 border-gray-300'
            }`}
            whileHover={{ scale: 1.05 }}
          >
            <div className="text-2xl mb-1">{phaseInfo.icon}</div>
            <div className="text-sm font-semibold">{phaseInfo.name}</div>
          </motion.div>
        ))}
      </div>

      {/* Stats Display */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{totalChunks}</div>
          <div className="text-sm text-blue-800">Research Chunks Stored</div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-purple-600">{semanticQueries.length}</div>
          <div className="text-sm text-purple-800">Semantic Searches</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-green-600">{insightCategories}</div>
          <div className="text-sm text-green-800">Insight Categories</div>
        </div>
      </div>

      {/* Current Activity */}
      {currentPhase === 'analysis' && currentQuery && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 bg-gradient-to-r from-purple-100 to-blue-100 rounded-lg"
        >
          <div className="flex items-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              className="text-2xl mr-3"
            >
              🔍
            </motion.div>
            <div>
              <div className="font-semibold text-gray-800">Currently Analyzing:</div>
              <div className="text-purple-700">{currentQuery}</div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Semantic Queries List */}
      {semanticQueries.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            🎯 Semantic Analysis Queries
          </h3>
          <div className="space-y-2">
            {semanticQueries.map((query, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center p-2 bg-gray-50 rounded"
              >
                <div className="w-2 h-2 bg-purple-500 rounded-full mr-3" />
                <span className="text-sm text-gray-700">{query}</span>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: index * 0.1 + 0.5 }}
                  className="ml-auto text-green-500"
                >
                  ✓
                </motion.div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Real-time Updates Feed */}
      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">
          📊 Real-time Processing Log
        </h3>
        <AnimatePresence>
          {updates.slice(-10).reverse().map((update, index) => (
            <motion.div
              key={`${update.timestamp}-${index}`}
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mb-3 p-3 bg-white rounded border-l-4 border-blue-500"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-semibold text-gray-800 text-sm">
                    {update.step}
                  </div>
                  <div className="text-gray-600 text-sm mt-1">
                    {update.reasoning}
                  </div>
                  {update.data && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {update.data.citations_count && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                          {update.data.citations_count} sources
                        </span>
                      )}
                      {update.data.stored_chunks && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                          {update.data.stored_chunks} chunks stored
                        </span>
                      )}
                      {update.data.insight_categories && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs">
                          {update.data.insight_categories} insights
                        </span>
                      )}
                      {update.data.research_chunks && (
                        <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs">
                          {update.data.research_chunks} chunks analyzed
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className={`ml-3 px-2 py-1 rounded-full text-xs ${
                  update.status === 'active' ? 'bg-yellow-100 text-yellow-800' :
                  update.status === 'complete' ? 'bg-green-100 text-green-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {update.status === 'active' ? '⏳' : update.status === 'complete' ? '✅' : '🎉'}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Technical Details Expandable */}
      <details className="mt-4">
        <summary className="cursor-pointer text-gray-600 text-sm hover:text-gray-800">
          🔧 Technical Details
        </summary>
        <div className="mt-2 p-3 bg-gray-50 rounded text-sm">
          <div className="space-y-1">
            <div><strong>Workflow ID:</strong> {workflowId}</div>
            <div><strong>Vector Storage:</strong> TiDB Serverless with semantic search</div>
            <div><strong>Embedding Model:</strong> text-embedding-004 (Google)</div>
            <div><strong>Search Threshold:</strong> 0.6 similarity</div>
            <div><strong>Chunk Size:</strong> 8000 characters max</div>
          </div>
        </div>
      </details>
    </div>
  );
};