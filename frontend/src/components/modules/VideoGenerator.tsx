"use client";

import { useState, useEffect } from "react";
import { useProjectStore } from "@/store/projectStore";
import VideoCreator from "./VideoCreator";
import VideoSidebar from "./VideoSidebar";
import { api, VideoTask } from "@/lib/api";

export default function VideoGenerator() {
    const currentProject = useProjectStore((state) => state.currentProject);
    const updateProject = useProjectStore((state) => state.updateProject);
    const [tasks, setTasks] = useState<VideoTask[]>([]);

    // Shared state for Remix functionality
    const [remixData, setRemixData] = useState<Partial<VideoTask> | null>(null);

    // Generation Params (Lifted State). The actual model now comes from
    // the project's i2v_instance_id at runtime — leaving ``model`` empty
    // tells the backend to resolve it from the instance.
    const [params, setParams] = useState({
        resolution: "720p",
        duration: 5,
        seed: undefined as number | undefined,
        generateAudio: true,
        audioUrl: "",
        promptExtend: true,
        negativePrompt: "",
        batchSize: 1,
        cameraMovement: "none" as string,
        subjectMotion: "still" as string,
        model: "",
        i2vInstanceId: null as string | null,
        shotType: "single" as string,
        generationMode: "i2v" as string,
        referenceVideoUrls: [] as string[],
        // Kling params
        mode: "std" as string,
        sound: false,
        cfgScale: 0.5,
        // Vidu params
        viduAudio: true,
        movementAmplitude: "auto" as string,
    });

    // Sync tasks from project
    useEffect(() => {
        if (currentProject?.video_tasks) {
            setTasks(currentProject.video_tasks);
        }
    }, [currentProject?.video_tasks]);

    // Poll for updates
    useEffect(() => {
        const hasActiveTasks = tasks.some(t => t.status === "pending" || t.status === "processing");
        if (!hasActiveTasks || !currentProject) return;

        const interval = setInterval(async () => {
            try {
                const project = await api.getProject(currentProject.id);
                if (project.video_tasks) {
                    setTasks(project.video_tasks);
                    updateProject(currentProject.id, { video_tasks: project.video_tasks });
                }
            } catch (error) {
                console.error("Failed to poll project status:", error);
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [tasks, currentProject?.id]);

    const handleTaskCreated = (updatedProject: any) => {
        if (updatedProject.video_tasks) {
            setTasks(updatedProject.video_tasks);
            updateProject(currentProject!.id, { video_tasks: updatedProject.video_tasks });
        }
    };

    const handleRemix = (task: VideoTask) => {
        setRemixData({
            image_url: task.image_url,
            prompt: task.prompt,
            negative_prompt: task.negative_prompt,
            seed: task.seed,
            duration: task.duration,
            audio_url: task.audio_url,
            prompt_extend: task.prompt_extend
        });

        // Update params state
        setParams(p => ({
            ...p,
            duration: task.duration || 5,
            seed: task.seed,
            resolution: task.resolution || "720p",
            generateAudio: task.generate_audio,
            audioUrl: task.audio_url || "",
            promptExtend: task.prompt_extend ?? true,
            negativePrompt: task.negative_prompt || "",
            // Reset motion params as they are not stored directly in task (they are in prompt)
            cameraMovement: "none",
            subjectMotion: "still"
        }));
    };

    return (
        <div className="flex h-full w-full overflow-hidden">
            {/* Left: Creator (70%) */}
            <div className="w-[70%] h-full border-r border-white/10">
                <VideoCreator
                    onTaskCreated={handleTaskCreated}
                    remixData={remixData}
                    onRemixClear={() => setRemixData(null)}
                    params={params}
                    onParamsChange={(newParams) => setParams(p => ({ ...p, ...newParams }))}
                />
            </div>

            {/* Right: Sidebar (30%) */}
            <div className="w-[30%] h-full">
                <VideoSidebar
                    tasks={tasks}
                    onRemix={handleRemix}
                    params={params}
                    setParams={setParams}
                />
            </div>
        </div>
    );
}
