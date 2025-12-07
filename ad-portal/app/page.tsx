import AdSubmissionForm from "./components/AdSubmissionForm";

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white selection:bg-neutral-700 selection:text-white pb-20">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
      <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black pointer-events-none"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 md:pt-20">
        <div className="flex flex-col items-center justify-center mb-12">
          <div className="flex items-center gap-3 mb-6">
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-10 w-10 fill-white"><g><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"></path></g></svg>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tighter">Ad Portal</h1>
          </div>
          <p className="text-neutral-400 text-lg max-w-2xl text-center">
            Create hyper-personalized advertising campaigns that adapt and resonate with every single user.
          </p>
        </div>
        
        <AdSubmissionForm />
        
        <footer className="mt-16 text-center text-neutral-600 text-sm">
          <p>&copy; {new Date().getFullYear()} X Corp. All rights reserved.</p>
        </footer>
      </div>
    </main>
  );
}
