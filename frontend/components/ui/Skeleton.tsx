import React from "react";
import { cn } from "@/utils/cn"; // Checking if clsx/tailwind-merge are used

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-slate-200/60 dark:bg-slate-800/60",
        className
      )}
      {...props}
    />
  );
}

export function ArticleSkeleton() {
  return (
    <div className="p-5 bg-white border border-slate-100 rounded-3xl shadow-sm space-y-4">
      <Skeleton className="h-4 w-1/4 rounded-full" />
      <Skeleton className="h-8 w-full rounded-xl" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-full rounded-lg" />
        <Skeleton className="h-4 w-[90%] rounded-lg" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  );
}

export function AnalysisSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-10 w-3/4 rounded-2xl" />
        <Skeleton className="h-4 w-1/4 rounded-lg" />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-red-50/30 rounded-[32px] border border-red-100 space-y-4">
          <Skeleton className="h-6 w-24 rounded-full bg-red-100" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-[80%]" />
          </div>
        </div>
        <div className="p-6 bg-slate-50 rounded-[32px] border border-slate-200 space-y-4">
          <Skeleton className="h-6 w-24 rounded-full bg-slate-200" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-[80%]" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function StoryboardSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 p-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="aspect-video bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-col justify-end">
          <Skeleton className="h-4 w-full mb-2" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      ))}
    </div>
  );
}
