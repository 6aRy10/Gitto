'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { api } from '../lib/api';
import { Check, X, AlertCircle, ChevronRight, FileText, Settings } from "lucide-react";

interface MappingProps {
  columns: string[];
  onConfirm: (mapping: Record<string, string>) => void;
  onCancel: () => void;
  sourceType: string;
}

export default function MappingUI({ columns, onConfirm, onCancel, sourceType }: MappingProps) {
  const [mapping, setMapping] = useState<Record<string, string>>({});
  
  const canonicalFields = [
    { id: 'document_number', label: 'Invoice Number', required: true },
    { id: 'customer', label: 'Customer Name', required: true },
    { id: 'amount', label: 'Invoice Amount', required: true },
    { id: 'currency', label: 'Currency', required: true },
    { id: 'expected_due_date', label: 'Due Date', required: true },
    { id: 'document_date', label: 'Document Date', required: false },
    { id: 'project', label: 'Project Name', required: false },
    { id: 'country', label: 'Country', required: false },
    { id: 'terms_of_payment', label: 'Payment Terms', required: false },
  ];

  useEffect(() => {
    // Try to auto-map based on name similarity
    const autoMap: Record<string, string> = {};
    canonicalFields.forEach(field => {
      const match = columns.find(col => 
        col.toLowerCase().replace(/[^a-z]/g, '') === field.id.toLowerCase().replace(/[^a-z]/g, '') ||
        col.toLowerCase().includes(field.label.toLowerCase())
      );
      if (match) autoMap[field.id] = match;
    });
    setMapping(autoMap);
  }, [columns]);

  const handleSelect = (fieldId: string, sourceCol: string) => {
    setMapping(prev => ({ ...prev, [fieldId]: sourceCol }));
  };

  const isComplete = canonicalFields.filter(f => f.required).every(f => !!mapping[f.id]);

  return (
    <Card className="max-w-4xl mx-auto rounded-[40px] border-slate-100 shadow-2xl bg-white overflow-hidden">
      <CardHeader className="p-10 border-b border-slate-50 bg-slate-50/50">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 text-[10px] font-black uppercase tracking-widest text-blue-600">
              <Settings className="h-3 w-3 mr-1.5" /> Source Mapping Engine
            </div>
            <CardTitle className="text-3xl font-black tracking-tighter italic">Map Your Data.</CardTitle>
            <CardDescription className="text-slate-500 font-medium">Link your source columns to Gitto's canonical schema.</CardDescription>
          </div>
          <FileText className="h-12 w-12 text-slate-200" />
        </div>
      </CardHeader>
      <CardContent className="p-10">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-black uppercase text-[10px] tracking-widest">Gitto Field</TableHead>
              <TableHead className="font-black uppercase text-[10px] tracking-widest text-center">Status</TableHead>
              <TableHead className="font-black uppercase text-[10px] tracking-widest">Source Column</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {canonicalFields.map((field) => (
              <TableRow key={field.id} className="hover:bg-slate-50/50 transition-colors">
                <TableCell className="py-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-black text-slate-900">{field.label}</span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{field.id}</span>
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  {mapping[field.id] ? (
                    <Check className="h-4 w-4 text-emerald-500 mx-auto" />
                  ) : field.required ? (
                    <AlertCircle className="h-4 w-4 text-red-400 mx-auto" />
                  ) : (
                    <div className="h-4 w-4 border-2 border-slate-100 rounded-full mx-auto" />
                  )}
                </TableCell>
                <TableCell>
                  <select 
                    className="w-full h-10 px-4 rounded-xl border-2 border-slate-100 bg-slate-50 text-xs font-bold focus:border-blue-500 focus:ring-0 transition-all"
                    value={mapping[field.id] || ''}
                    onChange={(e) => handleSelect(field.id, e.target.value)}
                  >
                    <option value="">Select Column...</option>
                    {columns.map(col => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <div className="mt-10 flex items-center justify-between pt-10 border-t border-slate-50">
          <Button variant="ghost" onClick={onCancel} className="text-[10px] font-black uppercase tracking-widest text-slate-400">
            <X className="mr-2 h-4 w-4" /> Cancel Import
          </Button>
          <div className="flex items-center gap-4">
            {!isComplete && (
              <span className="text-[10px] font-black text-red-500 uppercase tracking-widest animate-pulse">Required fields missing</span>
            )}
            <Button 
              disabled={!isComplete}
              onClick={() => onConfirm(mapping)}
              className="bg-slate-900 text-white hover:bg-blue-600 rounded-2xl px-10 h-14 font-black uppercase text-xs shadow-xl shadow-slate-200"
            >
              Confirm Mapping <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

