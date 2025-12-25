import { useMutation, useQueryClient } from "@tanstack/react-query";
import { composioKeys } from "./keys";
import { composioApi, CreateProfileRequest } from "./utils";

export const useCreateProfile = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (request: CreateProfileRequest) => composioApi.createProfile(request),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: composioKeys.profiles.all() });
        },
    });
};

export const useDeleteProfile = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (profileId: string) => composioApi.deleteProfile(profileId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: composioKeys.profiles.all() });
        },
    });
};

export const useBulkDeleteProfiles = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (profileIds: string[]) => composioApi.bulkDeleteProfiles(profileIds),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: composioKeys.profiles.all() });
        },
    });
};

export const useSetDefaultProfile = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (profileId: string) => composioApi.setDefaultProfile(profileId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: composioKeys.profiles.all() });
        },
    });
};

export const useMarkProfileConnected = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (profileId: string) => composioApi.markConnected(profileId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: composioKeys.profiles.all() });
        },
    });
};
