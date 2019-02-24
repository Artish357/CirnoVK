head --bytes 50000 avi.jpg > head.jpg
tail --bytes=+50000 avi.jpg > tail.jpg
./mosh.sh tail.jpg 100
cat head.jpg mosh-results/result3.jpg > result.jpg
rm -rf head.jpg tail.jpg mosh-results
