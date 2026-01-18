'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { api } from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  confidence?: number;
  sources?: string[];
  follow_ups?: string[];
}

const SUGGESTED_QUESTIONS = [
  'Why is cash down this week?',
  'What is our forecast accuracy?',
  'Which customers are overdue?',
  'What is our runway?',
  'What is the reconciliation status?',
  'What are the key variances this period?',
];

export function AskAnalyst() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function sendMessage(question: string) {
    if (!question.trim()) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.post('/fpa-analyst/ask?entity_id=1', {
        question,
        user_id: 'dashboard_user',
        context: null,
      });

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.data?.answer || 'No response generated.',
        timestamp: new Date(),
        confidence: response.data?.confidence,
        sources: response.data?.sources,
        follow_ups: response.data?.follow_up_questions,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Failed to get response:', err);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your question. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  function handleSuggestedQuestion(question: string) {
    sendMessage(question);
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[600px]">
      {/* Chat Panel */}
      <Card className="lg:col-span-3 bg-zinc-900 border-zinc-800 flex flex-col">
        <CardHeader className="border-b border-zinc-800">
          <CardTitle className="text-zinc-200 text-lg flex items-center gap-2">
            <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            Ask the AI Analyst
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-zinc-600 mb-4">
                  <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h3 className="text-zinc-400 font-medium mb-2">Ask me anything about your finances</h3>
                <p className="text-zinc-500 text-sm">
                  I can help you understand cash positions, variances, forecasts, and more.
                </p>
              </div>
            ) : (
              messages.map(message => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.role === 'user'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-zinc-800 text-zinc-200'
                    }`}
                  >
                    <pre className="whitespace-pre-wrap font-sans text-sm">{message.content}</pre>
                    
                    {message.role === 'assistant' && (
                      <div className="mt-3 pt-3 border-t border-zinc-700 space-y-2">
                        {message.confidence !== undefined && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-zinc-400">Confidence:</span>
                            <span className={getConfidenceColor(message.confidence)}>
                              {(message.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}
                        
                        {message.sources && message.sources.length > 0 && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-zinc-400">Sources:</span>
                            <span className="text-zinc-300">{message.sources.join(', ')}</span>
                          </div>
                        )}
                        
                        {message.follow_ups && message.follow_ups.length > 0 && (
                          <div className="mt-2">
                            <span className="text-zinc-400 text-xs">Follow-up questions:</span>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {message.follow_ups.map((q, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => handleSuggestedQuestion(q)}
                                  className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 rounded text-emerald-400 transition-colors"
                                >
                                  {q}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className={`text-xs mt-2 ${message.role === 'user' ? 'text-emerald-200' : 'text-zinc-500'}`}>
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {loading && (
              <div className="flex justify-start">
                <div className="bg-zinc-800 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-emerald-500" />
                    <span className="text-zinc-400 text-sm">Analyzing...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-zinc-800">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask a question..."
                className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-zinc-200 focus:outline-none focus:border-emerald-500"
                disabled={loading}
              />
              <Button type="submit" disabled={loading || !input.trim()}>
                {loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Suggested Questions */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-zinc-200 text-lg">Suggested Questions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {SUGGESTED_QUESTIONS.map((question, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestedQuestion(question)}
                disabled={loading}
                className="w-full text-left p-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm transition-colors disabled:opacity-50"
              >
                {question}
              </button>
            ))}
          </div>
          
          <div className="mt-6 pt-4 border-t border-zinc-800">
            <h4 className="text-zinc-400 text-sm font-medium mb-2">About the AI Analyst</h4>
            <p className="text-zinc-500 text-xs">
              The AI FP&A Analyst uses your financial data to answer questions about cash positions, 
              forecasts, variances, and reconciliation status. Answers are generated using real-time 
              data from your connected sources.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default AskAnalyst;
