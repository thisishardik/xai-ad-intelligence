 "use client";

import React, { useState, useRef } from 'react';
import { Upload, X, Check, Loader2, Send } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

interface AdFormData {
  companyName: string;
  adTitle: string;
  adContent: string;
  adImage: File | null;
  companyPersona: string;
  strictlyAgainst: string;
}

export default function AdSubmissionForm() {
  const [formData, setFormData] = useState<AdFormData>({
    companyName: '',
    adTitle: '',
    adContent: '',
    adImage: null,
    companyPersona: '',
    strictlyAgainst: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFormData(prev => ({ ...prev, adImage: file }));
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setFormData(prev => ({ ...prev, adImage: file }));
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const removeImage = () => {
    setFormData(prev => ({ ...prev, adImage: null }));
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      let imageUrl: string | null = null;

      // 1) Upload image to Supabase Storage (if provided)
      if (formData.adImage) {
        const file = formData.adImage;
        const fileExt = file.name.split('.').pop() || 'png';
        const fileName = `${crypto.randomUUID()}.${fileExt}`;
        const filePath = `ads/${fileName}`;

        const { data: img, error: imgErr } = await supabase.storage
          .from('ad-images')
          .upload(filePath, file);

        if (imgErr) {
          console.error('Supabase upload error:', imgErr);
          // Temporary surface for debugging
          if (typeof window !== 'undefined') {
            alert(`Upload error: ${imgErr.message ?? 'Unknown upload error'}`);
          }
          throw imgErr;
        }

        const { data: urlData } = supabase.storage
          .from('ad-images')
          .getPublicUrl(img.path);

        imageUrl = urlData.publicUrl;
      }

      // 2) Insert metadata into ad_campaigns table
      const { error } = await supabase
        .from('ad_campaigns')
        .insert({
          title: formData.adTitle,
          description: formData.adContent,
          company: formData.companyName,
          tagline: formData.companyPersona,
          image_url: imageUrl,
          // created_by: user?.id ?? null, // hook up when you have auth/user
          company_persona: formData.companyPersona,
          strictly_against: formData.strictlyAgainst,
        });

      if (error) throw error;

      // Reset form after success
      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        setFormData({
          companyName: '',
          adTitle: '',
          adContent: '',
          adImage: null,
          companyPersona: '',
          strictlyAgainst: '',
        });
        setPreviewUrl(null);
      }, 3000);
    } catch (error) {
      console.error('Error submitting form:', error);
      if (error instanceof Error && typeof window !== 'undefined') {
        alert(`Submission error: ${error.message}`);
      }
      // TODO: optionally surface a toast / inline error state
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden">
      <div className="p-8 md:p-10">
        <div className="mb-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">Create Campaign</h2>
          <p className="text-neutral-400">Launch your ad on the X platform</p>
        </div>

        {isSuccess ? (
          <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-500">
            <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mb-4 text-green-500">
              <Check size={32} strokeWidth={3} />
            </div>
            <h3 className="text-2xl font-bold text-white mb-2">Submission Received!</h3>
            <p className="text-neutral-400">Your campaign is being processed.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Company Info */}
            <div className="space-y-4">
              <div>
                <label htmlFor="companyName" className="block text-sm font-medium text-neutral-300 mb-1.5">
                  Company Name
                </label>
                <input
                  type="text"
                  id="companyName"
                  name="companyName"
                  required
                  value={formData.companyName}
                  onChange={handleChange}
                  placeholder="e.g. Acme Corp"
                  className="w-full px-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-white placeholder-neutral-500"
                />
              </div>
            </div>

            {/* Ad Details */}
            <div className="space-y-4">
              <div>
                <label htmlFor="adTitle" className="block text-sm font-medium text-neutral-300 mb-1.5">
                  Advertisement Title
                </label>
                <input
                  type="text"
                  id="adTitle"
                  name="adTitle"
                  required
                  value={formData.adTitle}
                  onChange={handleChange}
                  placeholder="Catchy headline for your ad"
                  className="w-full px-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-white placeholder-neutral-500"
                />
              </div>

              <div>
                <label htmlFor="adContent" className="block text-sm font-medium text-neutral-300 mb-1.5">
                  Advertisement Content
                </label>
                <textarea
                  id="adContent"
                  name="adContent"
                  required
                  value={formData.adContent}
                  onChange={handleChange}
                  placeholder="Main body text of your advertisement..."
                  rows={4}
                  className="w-full px-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-white placeholder-neutral-500 resize-none"
                />
              </div>
            </div>

            {/* Image Upload */}
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-1.5">
                Ad Creative
              </label>
              <div 
                className={`relative border-2 border-dashed rounded-xl transition-all duration-200 ease-in-out ${
                  previewUrl 
                    ? 'border-neutral-700 bg-neutral-900' 
                    : 'border-neutral-700 hover:border-blue-500/50 hover:bg-neutral-800/30 bg-neutral-800/20'
                }`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept="image/*"
                  className="hidden"
                />

                {previewUrl ? (
                  <div className="relative group p-2">
                    <img 
                      src={previewUrl} 
                      alt="Ad Preview" 
                      className="w-full h-48 object-cover rounded-lg"
                    />
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-lg">
                      <button
                        type="button"
                        onClick={removeImage}
                        className="p-2 bg-red-500/80 hover:bg-red-600 text-white rounded-full transition-colors"
                      >
                        <X size={20} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div 
                    className="flex flex-col items-center justify-center py-10 cursor-pointer"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div className="w-12 h-12 bg-neutral-700/50 rounded-full flex items-center justify-center mb-3 text-neutral-400">
                      <Upload size={24} />
                    </div>
                    <p className="text-sm font-medium text-neutral-300">
                      Click to upload or drag and drop
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">
                      SVG, PNG, JPG or GIF (max. 5MB)
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-neutral-800 my-6"></div>

            {/* AI Persona Configuration */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-lg font-semibold text-white">AI Configuration</h3>
                <span className="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400 font-medium border border-blue-500/20">
                  Generator Settings
                </span>
              </div>
              
              <div>
                <label htmlFor="companyPersona" className="block text-sm font-medium text-neutral-300 mb-1.5">
                  Company Persona
                </label>
                <div className="relative">
                  <textarea
                    id="companyPersona"
                    name="companyPersona"
                    required
                    value={formData.companyPersona}
                    onChange={handleChange}
                    placeholder="Describe your brand's voice, tone, and personality. This will guide the AI in generating future variations..."
                    rows={4}
                    className="w-full px-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all text-white placeholder-neutral-500 resize-none"
                  />
                  <div className="absolute top-3 right-3 pointer-events-none text-purple-500/20">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a10 10 0 1 0 10 10H12V2z"></path><path d="M12 2a10 10 0 0 1 10 10"></path><path d="M2 12h10"></path></svg>
                  </div>
                </div>
                <p className="text-xs text-neutral-500 mt-1.5">
                  Tip: Be specific about your target audience and key value propositions.
                </p>
              </div>

              <div>
                <label htmlFor="strictlyAgainst" className="block text-sm font-medium text-neutral-300 mb-1.5">
                  Strictly Against
                </label>
                <textarea
                  id="strictlyAgainst"
                  name="strictlyAgainst"
                  value={formData.strictlyAgainst}
                  onChange={handleChange}
                  placeholder="List any topics, words, or imagery that should strictly be avoided in your ads..."
                  rows={3}
                  className="w-full px-4 py-3 bg-neutral-800/50 border border-red-900/30 rounded-lg focus:ring-2 focus:ring-red-500/50 focus:border-transparent outline-none transition-all text-white placeholder-neutral-500 resize-none"
                />
              </div>
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-white text-black hover:bg-neutral-200 font-bold py-3.5 px-6 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Send size={20} />
                    Launch Campaign
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
