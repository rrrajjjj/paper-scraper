import concurrent.futures
import requests
from bs4 import BeautifulSoup
import csv
import PyPDF2
import io
import re
from tqdm import tqdm
import warnings 
warnings.filterwarnings("ignore")

def extract_text_from_pdf(pdf_url):
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with io.BytesIO(response.content) as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(pdf_reader.pages)
            
            conclusion_text = ""
            start_conclusion = False
            start_references = False
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                
                if "Conclusion" in page_text:
                    start_conclusion = True
                    page_text = page_text.split("Conclusion")[1]
                elif "Discussion" in page_text:
                    start_conclusion = True
                    page_text = page_text.split("Discussion")[1]

                if start_conclusion and "References" in page_text:
                    start_references = True
                    page_text = page_text.split("References")[0]
                
                if start_conclusion or start_references:
                    conclusion_text += page_text
        
                    
            return conclusion_text.strip()
    else:
        return None

def scrape_papers_from_neurips(years, output_csv):
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Title', 'Abstract', 'Conclusion']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for year in years:
            base_url = f"https://papers.nips.cc/paper/{year}"
            response = requests.get(base_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                paper_links = soup.find_all('a', href=re.compile(r'^/paper_files/'))
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = list(tqdm(executor.map(process_paper, paper_links), total=len(paper_links)))
                    for result in results:
                        if result:
                            writer.writerow(result)
            else:
                print(f"Error: Unable to access NeurIPS proceedings for the year {year}")

def process_paper(link):
    pdf_link = f"https://papers.nips.cc{link['href'].replace('Abstract-Conference.html', 'Paper-Conference.pdf').replace('hash', 'file')}"
    title, abstract = scrape_paper(link['href'])
    if title:
        try:
            conclusion = extract_text_from_pdf(pdf_link)
            return {'Title': title, 'Abstract': abstract, 'Conclusion': conclusion}
        except:
            return {'Title': title, 'Abstract': abstract, 'Conclusion': None}
    else:
        return None

def scrape_paper(url):
    response = requests.get(f"https://papers.nips.cc{url}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.text.strip()
        abstract = soup.find_all('p')[3].text.strip()  # 4th <p> tag
        return title, abstract
    else:
        print(f"Error: Unable to access paper at URL {url}")
        return None, None

# Main function
if __name__ == "__main__":
    years = [2023, 2022, 2021, 2020]  
    output_csv = "neurips_papers.csv"
    scrape_papers_from_neurips(years, output_csv)
