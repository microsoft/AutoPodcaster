using AutoPodcaster.Models;

public interface IInputService
{
    // Task<String> GetInputsAsync();
    Task<IQueryable<Input>> GetInputsAsync();
    Task IndexInputAsync(string content);
    Task IndexFileInputAsync(string fileName, FileInfo file, string contentType);
}