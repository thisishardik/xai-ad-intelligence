# X Ad Portal

A modern, sleek advertising portal interface designed for the X platform. This application allows companies to submit ad campaigns with detailed specifications, including creative assets and AI persona configurations for future generative ad variations.

![X Ad Portal](https://upload.wikimedia.org/wikipedia/commons/5/5a/X_icon_2.svg)

## Features

- **Modern Dark UI**: A beautiful, dark-themed interface inspired by the X design language.
- **Campaign Submission**: Easy-to-use form for company details, ad titles, and content.
- **Drag & Drop Upload**: Intuitive image upload with instant preview for ad creatives.
- **AI Configuration**: Special fields to define "Company Persona" and strict constraints ("Strictly Against") to guide LLM-based ad generation.
- **Responsive Design**: Fully responsive layout that works on desktop and mobile.

## Tech Stack

- **Framework**: [Next.js 15](https://nextjs.org/) (App Router)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Language**: TypeScript

## Getting Started

### Prerequisites

- Node.js 18.17 or later
- npm or yarn

### Installation

1. Navigate to the project directory:
   ```bash
   cd ad-portal
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

- `app/page.tsx`: The main landing page containing the layout.
- `app/components/AdSubmissionForm.tsx`: The primary form component with validation and state management.
- `app/globals.css`: Global styles and Tailwind configuration.

## Backend Integration

The form is currently set up with a placeholder for **Supabase** integration.

To connect a real backend:
1. Locate the `handleSubmit` function in `app/components/AdSubmissionForm.tsx`.
2. Replace the `setTimeout` simulation with your actual Supabase client code:

```typescript
// Example Supabase upload logic
const { data, error } = await supabase
  .from('campaigns')
  .insert([
    { 
      company_name: formData.companyName,
      ad_title: formData.adTitle,
      // ... other fields
    },
  ]);
```

## License

[MIT](https://choosealicense.com/licenses/mit/)
