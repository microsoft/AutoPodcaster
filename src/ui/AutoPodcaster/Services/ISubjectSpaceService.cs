using AutoPodcaster.Models;

public interface ISubjectSpaceService
{
    Task<IQueryable<SubjectSpace>> GetSubjectSpacesAsync();
    Task<SubjectSpace> GetSubjectSpaceByIdAsync(string id);
    Task CreateSubjectSpaceAsync(string subject);
    Task DeleteSubjectSpaceAsync(string id);
}