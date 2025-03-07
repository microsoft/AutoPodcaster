namespace AutoPodcaster.Models;

public sealed class Input
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string? Title { get; set; }
    public string? Date { get; set; }
    public string? LastUpdated { get; set; }
    public string? Status { get; set; }
    public string? Author { get; set; }
    public string? Description { get; set; }
    public string? Source { get; set; }
    public string? Type { get; set; }
    public string? ThumbnailUrl { get; set; }
    public List<string>? Topics { get; set; }
    public List<string>? Entities { get; set; }
    public string? Content { get; set; }
}