namespace AutoPodcaster.Models;

public sealed class SubjectSpace
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string? Subject { get; set; }
    public string? Date { get; set; }
    public string? LastUpdated { get; set; }
    public List<string>? InputIds { get; set; }
    public string? IndexName { get; set; }
}