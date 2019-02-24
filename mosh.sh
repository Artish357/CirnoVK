mkdir mosh
cp $1 ./mosh/file.jpg
size=$(ls -l ./mosh/file.jpg | cut -d " " -f5)
let frac=$size/$2
echo $frac
mkdir mosh/parts
if [ -d "./mosh-results" ]; then
    rm -rf ./mosh-results
fi
mkdir mosh-results
split -b $frac ./mosh/file.jpg ./mosh/parts/x
for i in {0..9}; do
    for f in $(ls ./mosh/parts); do
        cat ./mosh/parts/$f >> ./mosh-results/result$i.jpg
        echo $(expr $RANDOM%256 ) >> ./mosh-results/result$i.jpg
    done
done
rm -rf mosh

