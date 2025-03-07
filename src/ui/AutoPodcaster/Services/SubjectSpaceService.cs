using AutoPodcaster.Models;
using System.Net.Http.Json;

namespace AutoPodcaster.Services;

public class SubjectSpaceService([FromKeyedServices("SubjectSpaceBackend")] HttpClient http) : ISubjectSpaceService
{
    public async Task<IQueryable<SubjectSpace>> GetSubjectSpacesAsync()
    {
        return (await http.GetFromJsonAsync<SubjectSpace[]>("subjects") ?? []).AsQueryable();
    }

    public async Task<SubjectSpace> GetSubjectSpaceByIdAsync(string id)
    {
        return await http.GetFromJsonAsync<SubjectSpace>($"subjects/{id}") ?? throw new KeyNotFoundException();
    }

    private class SubjectSpaceContent(string subject)
    {
        public string subject { get; set; } = subject;
    }

    public async Task CreateSubjectSpaceAsync(string subject)
    {
        var content = JsonContent.Create(new SubjectSpaceContent(subject));
        await http.PostAsync("subjects", content);
    }

    public async Task DeleteSubjectSpaceAsync(string id)
    {
        await http.DeleteAsync($"subjects/{id}");
    }
}