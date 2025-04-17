# CV to HTML Converter Feature Plan

## Feature Overview

This feature will add a new section to the front page (index.html) that allows users to:
1. Upload a CV (PDF)
2. Process it with GPT-4 to extract the structure and content
3. Generate an HTML representation that matches the original layout
4. View and download the HTML version

## Implementation Plan

### 1. Enhance the CV Processor Module

We will extend the current CV processor module to include functionality for converting PDFs to structured HTML. This will involve:

- Creating a new function that extracts text from PDF files (using the existing functionality)
- Adding a function that analyzes the PDF structure to understand the layout, including:
  - Page dimensions
  - Text block positions
  - Font information
  - Visual hierarchy
- Developing a function that uses GPT-4 to convert the extracted text and structural information into well-formatted HTML
- Ensuring the HTML output maintains the visual appearance of the original PDF

The GPT-4 prompt will be carefully crafted to instruct the model to generate HTML that preserves the layout, styling, and structure of the original CV. The prompt will include detailed information about the PDF structure to help the model understand the spatial relationships between elements.

### 2. Update the Dashboard Application

The dashboard application will be modified to support the new CV-to-HTML conversion feature:

- Add a new route to handle CV uploads specifically for HTML conversion
- Implement background processing for the conversion task, as it may take some time
- Create a progress tracking system to keep users informed about the conversion status
- Add functionality to save the generated HTML to a file
- Develop a route for viewing the HTML version of the CV
- Add a download option for the HTML file

The conversion process will run in a background thread to keep the UI responsive, with progress updates provided to the user.

### 3. Create New HTML Templates

Three new HTML templates will be created:

1. **Front Page Addition**: A new card on the front page that allows users to upload a CV for HTML conversion
2. **CV HTML View Template**: A template for displaying the converted HTML CV with options to print or download
3. **Loading Template**: A template that shows a progress indicator while the conversion is in progress

The CV HTML view template will include proper styling to display the CV in an A4 page format, with print-friendly settings.

### 4. Add A4 Page Styling

We will add CSS styles to support A4 page formatting:

- Define the A4 page dimensions (210mm × 297mm)
- Add appropriate margins and padding
- Implement print-specific styles that remove UI elements and optimize for printing
- Create a set of CSS classes for common CV elements (headers, sections, entries, etc.)

The styling will ensure that the HTML representation looks professional and matches the original PDF layout as closely as possible.

## Important Considerations

1. **PDF Structure Extraction**: 
   - The feature relies on PyMuPDF's ability to extract structured information from PDFs
   - Different PDF formats and structures may present challenges
   - We need robust error handling for various PDF layouts

2. **GPT Model Selection and Prompt Engineering**: 
   - We use GPT-4.1-mini instead of GPT-4.1 to avoid rate limit issues with large PDFs
   - The quality of the HTML output depends heavily on the prompt design
   - The prompt provides clear instructions about preserving layout and styling
   - We may need to iterate on the prompt based on testing results

3. **HTML/CSS Rendering**: 
   - Browser rendering differences may affect the final appearance
   - We need to ensure the HTML is responsive while maintaining the A4 aspect ratio
   - Print styling requires special attention to ensure good results when printed
   - **Direct embedding of HTML content** is more reliable than using iframes for displaying the converted CV

4. **Performance Considerations**: 
   - Processing large PDFs might take time
   - Background processing with status updates is implemented for better user experience
   - Progress modal shows real-time conversion status
   - We should consider caching results for previously processed CVs

5. **Error Handling**: 
   - Robust error handling for different PDF formats and structures
   - Graceful fallbacks if certain elements can't be properly converted
   - Clear error messages for users if conversion fails
   - Rate limit handling by using a smaller, more efficient model
   - **HTML content validation** to ensure proper structure and formatting

## Implementation Steps

1. Extend the CV processor module with the new conversion functions
2. Add the new routes to the dashboard application
3. Create the new HTML templates
4. Add the A4 page styling to the CSS
5. Test the feature with various CV formats and structures
6. Refine the GPT-4 prompt based on testing results
7. Implement error handling and edge cases
8. Add the feature to the front page

## User Experience Flow

1. User navigates to the dashboard front page
2. User clicks on the "Convert CV to HTML" card
3. User selects a PDF CV file and clicks "Convert to HTML"
4. System shows a loading screen with progress updates
5. Once processing is complete, the system displays the HTML version of the CV
6. User can view, print, or download the HTML version
7. User can return to the dashboard to process additional CVs

## Recent Improvements

### HTML Content Display Enhancement

We identified and fixed an issue where the HTML CV view was showing a blank white page. The solution involved:

1. **Direct HTML Embedding**: Modified the `cv_html_view.html` template to directly embed the HTML content instead of using an iframe, which provides more reliable rendering.

2. **CSS Styling Updates**: 
   - Updated the container styles to include proper padding (20mm) for A4 format
   - Improved print styles to ensure the CV is properly displayed when printed
   - Added overflow handling to ensure all content is visible

3. **HTML Content Validation**: 
   - Enhanced the `cv_to_html_converter.py` to validate the HTML content structure
   - Added automatic wrapping of content in proper HTML structure if needed
   - Included default CSS styles to ensure consistent rendering

These improvements ensure that the HTML representation of the CV is properly displayed in the browser and when printed, providing a better user experience.

This feature will enhance the system by providing users with a way to convert their CVs to web-friendly formats while preserving the original layout and styling.
